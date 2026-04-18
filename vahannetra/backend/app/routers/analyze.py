from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, status

from vahannetra.backend.app.auth import AuthPrincipal, get_current_principal
from vahannetra.backend.app.schemas import AnalyzeAccepted, AnalyzeInput, utc_now_iso

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeAccepted)
async def analyze(
    payload: AnalyzeInput,
    principal: AuthPrincipal = Depends(get_current_principal),
) -> AnalyzeAccepted:
    _ = principal
    job_id = f"JOB-{uuid4().hex[:12].upper()}"
    return AnalyzeAccepted(
        job_id=job_id,
        status="queued",
        message=f"Accepted {payload.media_type} payload with {payload.source_count} source(s)",
        queued_at=utc_now_iso(),
    )
