from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vahannetra.backend.app.auth import AuthPrincipal, get_current_principal
from vahannetra.backend.app.database import get_async_db
from vahannetra.backend.app.schemas import JobFrameItem, JobResultResponse
from vahannetra.backend.app.services.jobs import get_job_with_frames, job_created_at_iso

router = APIRouter(prefix="/api/v1", tags=["results"])


@router.get("/results/{job_id}", response_model=JobResultResponse)
async def get_results(
    job_id: str,
    _principal: AuthPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_async_db),
) -> JobResultResponse:
    job, frames = await get_job_with_frames(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobResultResponse(
        job_id=job.id,
        status=job.status,
        input_type=job.input_type,
        source_count=job.source_count,
        video_key=job.video_key,
        created_at=job_created_at_iso(job),
        frames=[JobFrameItem(frame_key=item.frame_key, sharpness=item.sharpness) for item in frames],
    )
