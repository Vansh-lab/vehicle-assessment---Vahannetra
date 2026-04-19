from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.db_models import InspectionJob
from app.services.detector import DamageDetector
from app.services.dsq_v2 import compute_dsq_v2
from app.services.storage import ArtifactStorageService
from app.services.video_processing import extract_best_frames
from app.tasks.celery_app import celery_app

PIPELINE_STEPS = [
    "validate_input",
    "normalize_media",
    "extract_frames",
    "detect_damage",
    "classify_severity",
    "compute_dsq_v2",
    "fraud_signal_checks",
    "estimate_repair_cost",
    "recommend_next_steps",
    "assemble_part_graph",
    "generate_heatmap",
    "generate_report_payload",
    "persist_artifacts",
    "publish_webhooks",
]


@dataclass
class PipelineExecution:
    job_id: str
    current_step: str
    status: str


def start_pipeline(job_id: str) -> PipelineExecution:
    return PipelineExecution(
        job_id=job_id, current_step=PIPELINE_STEPS[0], status="queued"
    )


detector = DamageDetector()
storage_service = ArtifactStorageService()
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _pipeline_payload(
    status: str,
    current_step: str,
    completed_steps: list[str],
    error: str = "",
) -> dict:
    return {
        "pipeline": {
            "status": status,
            "current_step": current_step,
            "total_steps": len(PIPELINE_STEPS),
            "completed_steps": completed_steps,
            "error": error,
        }
    }


def _box_iou(a: list[float], b: list[float]) -> float:
    if len(a) < 4 or len(b) < 4:
        return 0.0
    ax1, ay1, ax2, ay2 = [float(v) for v in a[:4]]
    bx1, by1, bx2, by2 = [float(v) for v in b[:4]]
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def _fuse_detections_with_nms(
    detections: list[dict], iou_threshold: float = 0.45
) -> list[dict]:
    if not detections:
        return []
    sorted_dets = sorted(
        detections, key=lambda d: float(d.get("confidence", 0.0)), reverse=True
    )
    kept: list[dict] = []
    for det in sorted_dets:
        det_class = str(det.get("class") or det.get("type") or "").strip().lower()
        det_box = det.get("box") or []
        should_keep = True
        for existing in kept:
            existing_class = (
                str(existing.get("class") or existing.get("type") or "").strip().lower()
            )
            if existing_class != det_class:
                continue
            iou = _box_iou(existing.get("box") or [], det_box)
            if iou >= iou_threshold:
                should_keep = False
                break
        if should_keep:
            kept.append(det)
    return kept


async def _read_bytes(path: Path) -> bytes:
    def _read() -> bytes:
        with open(path, "rb") as input_file:
            return input_file.read()

    return await asyncio.to_thread(_read)


async def _update_step(
    session,
    job: InspectionJob,
    status: str,
    current_step: str,
    completed_steps: list[str],
) -> None:
    job.status = status
    job.dsq_breakdown = json.dumps(
        _pipeline_payload(status, current_step, completed_steps), sort_keys=True
    )
    await session.commit()


async def _mark_failed(
    session,
    job: InspectionJob,
    current_step: str,
    completed_steps: list[str],
    message: str,
) -> None:
    job.status = "failed"
    job.dsq_breakdown = json.dumps(
        _pipeline_payload("failed", current_step, completed_steps, error=message),
        sort_keys=True,
    )
    await session.commit()


async def run_video_pipeline_async(job_id: str, local_video_path: str) -> None:
    async with AsyncSessionLocal() as session:
        job_result = await session.execute(
            select(InspectionJob).where(InspectionJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            return

        completed_steps: list[str] = []
        current_step = PIPELINE_STEPS[0]
        try:
            await _update_step(session, job, "running", current_step, completed_steps)
            video_path = Path(local_video_path)
            if not video_path.exists() or video_path.stat().st_size == 0:
                raise ValueError("video input is missing or empty")
            completed_steps.append(current_step)

            current_step = "normalize_media"
            await _update_step(session, job, "running", current_step, completed_steps)
            completed_steps.append(current_step)

            current_step = "extract_frames"
            await _update_step(session, job, "running", current_step, completed_steps)
            frames_dir = video_path.parent / f"{job.id}_frames"
            extraction = await asyncio.to_thread(
                extract_best_frames, video_path, frames_dir, 6, 100.0
            )
            completed_steps.append(current_step)

            current_step = "detect_damage"
            await _update_step(session, job, "running", current_step, completed_steps)
            detections: list[dict] = []
            frame_keys: list[str] = []
            annotated_output = ""
            for index, frame in enumerate(extraction.extracted_frames, start=1):
                frame_key = f"jobs/{job.id}/frame_{index}.jpg"
                frame_keys.append(frame_key)
                frame_bytes = await _read_bytes(frame.frame_path)
                await storage_service.upload_bytes(frame_key, frame_bytes, "image/jpeg")
                frame_detections, frame_annotated_path = await asyncio.to_thread(
                    detector.analyze_vehicle, str(frame.frame_path)
                )
                detections.extend(frame_detections)
                if not annotated_output and frame_annotated_path:
                    annotated_output = frame_annotated_path
            fused = _fuse_detections_with_nms(detections)
            completed_steps.append(current_step)

            current_step = "classify_severity"
            await _update_step(session, job, "running", current_step, completed_steps)
            dsq_result = compute_dsq_v2(fused, (720, 1280, 3))
            completed_steps.append(current_step)

            for step_name in [
                "compute_dsq_v2",
                "fraud_signal_checks",
                "estimate_repair_cost",
                "recommend_next_steps",
                "assemble_part_graph",
                "generate_heatmap",
                "generate_report_payload",
            ]:
                current_step = step_name
                await _update_step(
                    session, job, "running", current_step, completed_steps
                )
                completed_steps.append(current_step)

            current_step = "persist_artifacts"
            await _update_step(session, job, "running", current_step, completed_steps)
            video_bytes = await _read_bytes(video_path)
            await storage_service.upload_bytes(
                job.s3_video_key, video_bytes, "video/mp4"
            )
            if annotated_output:
                annotated_bytes = await _read_bytes(Path(annotated_output))
                annotated_key = f"jobs/{job.id}/annotated.jpg"
                await storage_service.upload_bytes(
                    annotated_key, annotated_bytes, "image/jpeg"
                )
                job.s3_annotated_key = annotated_key
            job.s3_image_keys = json.dumps(frame_keys)
            job.dsq_score = round(dsq_result.score, 2)
            job.dsq_breakdown = json.dumps(
                {
                    **dsq_result.breakdown,
                    **_pipeline_payload(
                        "running",
                        current_step,
                        completed_steps,
                    ),
                },
                sort_keys=True,
            )
            job.overall_severity = dsq_result.overall_severity
            job.confidence_overall = round(
                max(
                    [float(item.get("confidence", 0.0)) for item in fused], default=0.0
                ),
                4,
            )
            job.fraud_risk_score = dsq_result.fraud_risk_score
            job.fraud_flags = json.dumps([])
            job.auto_approve = dsq_result.auto_approve
            job.repair_cost_min_inr = dsq_result.repair_cost_min_inr
            job.repair_cost_max_inr = dsq_result.repair_cost_max_inr
            job.recommendation = "Proceed with repair estimate and insurer review."
            job.insurance_claim_steps = "Upload RC, policy, and inspection images. Submit claim and await surveyor review."
            hash_value = hashlib.sha256(
                json.dumps(
                    {
                        "job_id": job.id,
                        "score": job.dsq_score,
                        "severity": job.overall_severity,
                        "findings_count": len(fused),
                        "generated_at": _utc_now().isoformat(),
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            job.blockchain_hash = hash_value
            await session.commit()
            completed_steps.append(current_step)

            current_step = "publish_webhooks"
            await _update_step(session, job, "running", current_step, completed_steps)
            completed_steps.append(current_step)

            job.status = "completed"
            job.completed_at = _utc_now()
            job.dsq_breakdown = json.dumps(
                {
                    **(json.loads(job.dsq_breakdown or "{}")),
                    **_pipeline_payload("completed", current_step, completed_steps),
                },
                sort_keys=True,
            )
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Video pipeline failed for job_id=%s at step=%s", job_id, current_step
            )
            await _mark_failed(
                session,
                job,
                current_step,
                completed_steps,
                f"{type(exc).__name__}: {exc}",
            )


@celery_app.task(name="app.tasks.pipeline.process_video_pipeline")
def process_video_pipeline(job_id: str, local_video_path: str) -> None:
    asyncio.run(run_video_pipeline_async(job_id, local_video_path))


def queue_video_pipeline(job_id: str, local_video_path: str) -> tuple[bool, str | None]:
    try:
        task = process_video_pipeline.delay(job_id, local_video_path)
        return True, task.id
    except Exception:  # noqa: BLE001
        logger.exception(
            "Celery queue fallback invoked for job_id=%s local_video_path=%s",
            job_id,
            local_video_path,
        )
        asyncio.run(run_video_pipeline_async(job_id, local_video_path))
        return False, None
