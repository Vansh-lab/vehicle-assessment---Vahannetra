from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from vahannetra.backend.app.auth import AuthPrincipal, get_current_principal
from vahannetra.backend.app.core.settings import settings
from vahannetra.backend.app.database import get_async_db
from vahannetra.backend.app.schemas import (
    AnalyzeAccepted,
    AnalyzeInput,
    AnalyzeUrlInput,
    utc_now_iso,
)
from vahannetra.backend.app.services.jobs import (
    append_job_frame,
    create_job,
    set_job_result_json,
    set_job_status,
)
from vahannetra.backend.app.services.storage import storage_service
from vahannetra.backend.app.services.video_processing import extract_best_frames
from vahannetra.backend.app.tasks.pipeline import enqueue_pipeline

router = APIRouter(prefix="/api/v1", tags=["analyze"])
MIN_ESTIMATED_SECONDS = 3
MAX_ESTIMATED_SECONDS = 120
PIPELINE_OVERHEAD_SECONDS = 4


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeAccepted)
async def analyze(
    payload: AnalyzeInput,
    _principal: AuthPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_async_db),
) -> AnalyzeAccepted:
    job = await create_job(
        db, input_type=payload.media_type, source_count=payload.source_count
    )
    job_status = "queued"
    dispatch_state = enqueue_pipeline(job.id)
    if dispatch_state == "dispatched":
        job_status = "processing"
        await set_job_status(db, job_id=job.id, status="processing")
    return AnalyzeAccepted(
        job_id=job.id,
        status=job_status,
        message=f"Accepted {payload.media_type} payload with {payload.source_count} source(s)",
        queued_at=utc_now_iso(),
    )


@router.post(
    "/analyze/url", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeAccepted
)
async def analyze_url(
    payload: AnalyzeUrlInput,
    _principal: AuthPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_async_db),
) -> AnalyzeAccepted:
    job = await create_job(db, input_type="url", source_count=1)
    await set_job_result_json(
        db, job_id=job.id, result_json=json.dumps({"source_url": str(payload.source_url)})
    )

    dispatch_state = enqueue_pipeline(job.id)
    job_status = "queued"
    if dispatch_state == "dispatched":
        job_status = "processing"
        await set_job_status(db, job_id=job.id, status="processing")

    return AnalyzeAccepted(
        job_id=job.id,
        status=job_status,
        message=f"URL analysis accepted for {payload.source_url.host or 'source'}",
        queued_at=utc_now_iso(),
    )


@router.post(
    "/analyze/video", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeAccepted
)
async def analyze_video(
    file: UploadFile = File(...),
    _principal: AuthPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_async_db),
) -> AnalyzeAccepted:
    allowed_types = {"video/mp4", "video/webm", "video/quicktime"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only mp4, webm and mov video files are allowed",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded video is empty")
    if len(payload) > settings.max_video_size_bytes:
        raise HTTPException(status_code=413, detail="Video exceeds max size of 100MB")

    job = await create_job(db, input_type="video", source_count=1)
    video_key = f"jobs/{job.id}/input_video.mp4"
    stored_video_key = await storage_service.upload_bytes(video_key, payload)
    job.video_key = video_key
    await db.commit()

    temp_video = settings.artifacts_root / stored_video_key

    extraction = extract_best_frames(
        video_path=temp_video,
        output_dir=settings.artifacts_root / "extracted_frames" / job.id,
        n_frames=6,
        sharpness_threshold=100.0,
    )

    for index, frame in enumerate(extraction.frames, start=1):
        frame_key = f"jobs/{job.id}/frame_{index}.jpg"
        frame_bytes = Path(frame.frame_path).read_bytes()
        await storage_service.upload_bytes(frame_key, frame_bytes)
        await append_job_frame(
            db,
            job_id=job.id,
            frame_key=frame_key,
            sharpness=frame.sharpness,
        )

    dispatch_state = enqueue_pipeline(job.id)
    job_status = "queued"
    if dispatch_state == "dispatched":
        await set_job_status(db, job_id=job.id, status="processing")
        job_status = "processing"

    estimated_seconds = max(
        MIN_ESTIMATED_SECONDS,
        min(MAX_ESTIMATED_SECONDS, extraction.duration_seconds + PIPELINE_OVERHEAD_SECONDS),
    )
    return AnalyzeAccepted(
        job_id=job.id,
        status=job_status,
        message="Video analysis accepted",
        queued_at=utc_now_iso(),
        estimated_seconds=estimated_seconds,
    )
