import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async
from app.database import get_async_db
from app.db_models import InspectionJob, User
from app.services.detector import DamageDetector
from app.services.dsq_v2 import compute_dsq_v2
from app.services.storage import ArtifactStorageService
from app.services.video_processing import extract_best_frames
from app.utils.network import ensure_public_http_url

router = APIRouter(prefix="/api/v1", tags=["analyze"])

detector = DamageDetector()
storage_service = ArtifactStorageService()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class V1AnalyzeAccepted(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_seconds: int | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def extension_for_content_type(content_type: str | None, fallback: str = ".bin") -> str:
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if content_type == "video/mp4":
        return ".mp4"
    if content_type == "video/webm":
        return ".webm"
    if content_type in {"video/quicktime", "video/mov"}:
        return ".mov"
    return fallback


def _validate_upload(file: UploadFile, payload: bytes) -> None:
    max_size_bytes = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(8 * 1024 * 1024)))
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(payload) > max_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail="Only JPEG, PNG and WEBP files are allowed"
        )

    header = payload[:12]
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(status_code=400, detail="Invalid image signature")

    decoded = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(
            status_code=400, detail="Corrupt or unsupported image payload"
        )


def _validate_video_upload(file: UploadFile, payload: bytes) -> None:
    allowed_types = {"video/mp4", "video/webm", "video/quicktime", "video/mov"}
    max_size_bytes = int(
        os.getenv("MAX_VIDEO_UPLOAD_SIZE_BYTES", str(100 * 1024 * 1024))
    )
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded video is empty")
    if len(payload) > max_size_bytes:
        raise HTTPException(status_code=413, detail="Video exceeds max size of 100MB")
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail="Only mp4, webm and mov video files are allowed"
        )


def _write_bytes(path: Path, payload: bytes) -> None:
    with open(path, "wb") as output_file:
        output_file.write(payload)


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as input_file:
        return input_file.read()


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


def _fuse_detections_with_nms(detections: list[dict], iou_threshold: float = 0.45) -> list[dict]:
    if not detections:
        return []
    sorted_dets = sorted(detections, key=lambda d: float(d.get("confidence", 0.0)), reverse=True)
    kept: list[dict] = []
    for det in sorted_dets:
        det_class = str(det.get("class") or det.get("type") or "").strip().lower()
        det_box = det.get("box") or []
        should_keep = True
        for existing in kept:
            existing_class = str(existing.get("class") or existing.get("type") or "").strip().lower()
            if existing_class != det_class:
                continue
            iou = _box_iou(existing.get("box") or [], det_box)
            if iou >= iou_threshold:
                should_keep = False
                break
        if should_keep:
            kept.append(det)
    return kept


async def create_job_from_findings_async(
    db: AsyncSession,
    organization_id: str,
    findings: list[dict],
    input_type: str,
    annotated_key: str,
    image_keys: list[str] | None = None,
    video_key: str = "",
    status: str = "completed",
) -> InspectionJob:
    dsq_result = compute_dsq_v2(findings, (720, 1280, 3))
    score = dsq_result.score
    severity = dsq_result.overall_severity

    metadata_payload = {
        "organization_id": organization_id,
        "input_type": input_type,
        "image_keys": image_keys or [],
        "video_key": video_key,
        "annotated_key": annotated_key,
        "score": score,
        "severity": severity,
        "findings_count": len(findings),
        "generated_at": utc_now().isoformat(),
    }
    hash_value = hashlib.sha256(
        json.dumps(metadata_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    job = InspectionJob(
        id=f"JOB-{uuid.uuid4().hex[:12].upper()}",
        organization_id=organization_id,
        status=status,
        input_type=input_type,
        s3_image_keys=json.dumps(image_keys or []),
        s3_video_key=video_key,
        s3_annotated_key=annotated_key,
        dsq_score=round(score, 2),
        dsq_breakdown=json.dumps(dsq_result.breakdown),
        overall_severity=severity,
        confidence_overall=round(
            max([float(item.get("confidence", 0.0)) for item in findings], default=0.0),
            4,
        ),
        fraud_risk_score=dsq_result.fraud_risk_score,
        fraud_flags=json.dumps([]),
        auto_approve=dsq_result.auto_approve,
        repair_cost_min_inr=dsq_result.repair_cost_min_inr,
        repair_cost_max_inr=dsq_result.repair_cost_max_inr,
        recommendation="Proceed with repair estimate and insurer review.",
        insurance_claim_steps="Upload RC, policy, and inspection images. Submit claim and await surveyor review.",
        blockchain_hash=hash_value,
        completed_at=utc_now() if status == "completed" else None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/analyze", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    if len(files) < 1 or len(files) > 10:
        raise HTTPException(status_code=400, detail="Upload between 1 and 10 images")

    detections: list[dict] = []
    image_keys: list[str] = []
    annotated = ""
    for index, file in enumerate(files):
        payload = await file.read()
        await asyncio.to_thread(_validate_upload, file, payload)
        safe_name = (
            f"img_{uuid.uuid4().hex}"
            f"{extension_for_content_type(file.content_type, fallback='.jpg')}"
        )
        file_path = UPLOAD_DIR / safe_name
        await asyncio.to_thread(_write_bytes, file_path, payload)
        image_keys.append(f"uploads/{safe_name}")

        frame_detections, processed_img_path = await asyncio.to_thread(
            detector.analyze_vehicle, str(file_path)
        )
        detections.extend(frame_detections)
        if index == 0:
            annotated = f"uploads/{Path(processed_img_path).name}"

    fused = _fuse_detections_with_nms(detections)
    job = await create_job_from_findings_async(
        db,
        current_user.organization_id,
        fused,
        input_type="multi" if len(files) > 1 else "photo",
        annotated_key=annotated,
        image_keys=image_keys,
        status="completed",
    )
    return V1AnalyzeAccepted(
        job_id=job.id, status="queued", message="Analysis accepted"
    )


@router.post("/analyze/url", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze_url(
    image_url: str = Query(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    ensure_public_http_url(image_url)

    job = await create_job_from_findings_async(
        db,
        current_user.organization_id,
        [],
        input_type="photo",
        annotated_key="",
        image_keys=[image_url],
        status="queued",
    )
    return V1AnalyzeAccepted(
        job_id=job.id, status="queued", message="URL analysis accepted"
    )


@router.post("/analyze/video", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    payload = await file.read()
    await asyncio.to_thread(_validate_video_upload, file, payload)

    job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
    input_ext = extension_for_content_type(file.content_type, fallback=".webm")
    local_video_name = f"{job_id}_input{input_ext}"
    file_path = UPLOAD_DIR / local_video_name
    await asyncio.to_thread(_write_bytes, file_path, payload)

    frames_dir = UPLOAD_DIR / f"{job_id}_frames"
    extraction = await asyncio.to_thread(
        extract_best_frames, file_path, frames_dir, 6, 100.0
    )
    estimated_seconds = max(3, min(120, extraction.duration_seconds + 4))

    frame_keys: list[str] = []
    detections: list[dict] = []
    annotated_output = ""
    for index, frame in enumerate(extraction.extracted_frames, start=1):
        frame_key = f"jobs/{job_id}/frame_{index}.jpg"
        frame_keys.append(frame_key)
        try:
            frame_bytes = await asyncio.to_thread(_read_bytes, frame.frame_path)
            await storage_service.upload_bytes(frame_key, frame_bytes, "image/jpeg")
        except OSError:
            pass

        frame_detections, frame_annotated_path = await asyncio.to_thread(
            detector.analyze_vehicle, str(frame.frame_path)
        )
        detections.extend(frame_detections)
        if not annotated_output and frame_annotated_path:
            annotated_output = frame_annotated_path

    fused = _fuse_detections_with_nms(detections)

    # Fixed key contract from spec
    video_key = f"jobs/{job_id}/input_video.mp4"
    await storage_service.upload_bytes(
        video_key, payload, file.content_type or "video/webm"
    )

    if annotated_output:
        try:
            annotated_bytes = await asyncio.to_thread(
                _read_bytes, Path(annotated_output)
            )
            await storage_service.upload_bytes(
                f"jobs/{job_id}/annotated.jpg", annotated_bytes, "image/jpeg"
            )
        except OSError:
            pass

    job = await create_job_from_findings_async(
        db,
        current_user.organization_id,
        fused,
        input_type="video",
        annotated_key=f"jobs/{job_id}/annotated.jpg" if annotated_output else "",
        image_keys=frame_keys,
        video_key=video_key,
        status="completed",
    )
    return V1AnalyzeAccepted(
        job_id=job.id,
        status="queued",
        message="Video analysis accepted",
        estimated_seconds=estimated_seconds,
    )
