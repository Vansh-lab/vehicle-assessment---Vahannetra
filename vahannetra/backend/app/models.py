from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vahannetra.backend.app.database import Base


class AssessmentJob(Base):
    __tablename__ = "phase3_assessment_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    input_type: Mapped[str] = mapped_column(String(16), default="image", nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    video_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    frames: Mapped[list[JobFrame]] = relationship(
        "JobFrame",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobFrame(Base):
    __tablename__ = "phase3_job_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("phase3_assessment_jobs.id", ondelete="CASCADE"), nullable=False
    )
    frame_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sharpness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    job: Mapped[AssessmentJob] = relationship("AssessmentJob", back_populates="frames")
