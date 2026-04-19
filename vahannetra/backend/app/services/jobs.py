from __future__ import annotations

from datetime import timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vahannetra.backend.app.models import AssessmentJob, JobFrame


def _datetime_to_utc_iso(value) -> str:
    """Normalize a timezone-aware datetime to UTC ISO8601 with Z suffix."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def create_job(
    db: AsyncSession,
    *,
    input_type: str,
    source_count: int,
    video_key: str = "",
) -> AssessmentJob:
    job = AssessmentJob(
        id=f"JOB-{uuid4().hex[:12].upper()}",
        status="queued",
        input_type=input_type,
        source_count=source_count,
        video_key=video_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def append_job_frame(
    db: AsyncSession,
    *,
    job_id: str,
    frame_key: str,
    sharpness: float,
) -> None:
    db.add(JobFrame(job_id=job_id, frame_key=frame_key, sharpness=int(sharpness)))
    await db.commit()


async def set_job_status(db: AsyncSession, *, job_id: str, status: str) -> None:
    job = await get_job(db, job_id)
    if job is None:
        return
    job.status = status
    await db.commit()


async def get_job(db: AsyncSession, job_id: str) -> AssessmentJob | None:
    result = await db.execute(
        select(AssessmentJob).where(AssessmentJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_job_with_frames(db: AsyncSession, job_id: str) -> tuple[AssessmentJob | None, list[JobFrame]]:
    job = await get_job(db, job_id)
    if job is None:
        return None, []
    frames_result = await db.execute(
        select(JobFrame).where(JobFrame.job_id == job_id).order_by(JobFrame.id.asc())
    )
    return job, frames_result.scalars().all()


def job_created_at_iso(job: AssessmentJob) -> str:
    return _datetime_to_utc_iso(job.created_at)
