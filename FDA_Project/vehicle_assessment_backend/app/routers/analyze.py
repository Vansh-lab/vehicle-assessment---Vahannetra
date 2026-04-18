import asyncio
import hashlib
import hmac
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
from app.secrets import get_secret
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
    hash_payload = f"{organization_id}:{score}:{utc_now().isoformat()}"
    hash_secret_key = (
        get_secret("VAHANNETRA_HASH_SECRET", "vahannetra-hash-secret") or ""
    ).encode("utf-8")
    hash_value = hmac.new(
        hash_secret_key, hash_payload.encode("utf-8"), hashlib.sha256
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
        if index == 0:
            detections, processed_img_path = await asyncio.to_thread(
                detector.analyze_vehicle, str(file_path)
            )
            annotated = f"uploads/{Path(processed_img_path).name}"

    job = await create_job_from_findings_async(
        db,
        current_user.organization_id,
        detections,
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
    safe_name = (
        f"{job_id}_input"
        f"{extension_for_content_type(file.content_type, fallback='.webm')}"
    )
    file_path = UPLOAD_DIR / safe_name
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

    video_key = (
        f"jobs/{job_id}/input_video"
        f"{extension_for_content_type(file.content_type, fallback='.webm')}"
    )
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
        detections,
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
