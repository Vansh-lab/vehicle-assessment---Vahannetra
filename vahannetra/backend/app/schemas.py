from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str


class CapabilityResponse(BaseModel):
    backend_foundation: bool
    auth: bool
    async_db: bool
    routers: list[str]


class AnalyzeAccepted(BaseModel):
    job_id: str
    status: str
    message: str
    queued_at: str


class AnalyzeInput(BaseModel):
    media_type: str = Field(default="image", pattern="^(image|video|multi)$")
    source_count: int = Field(default=1, ge=1, le=10)


class PrincipalResponse(BaseModel):
    subject: str
    role: str
    organization_id: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
