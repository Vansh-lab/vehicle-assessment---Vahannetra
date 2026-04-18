from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from vahannetra.backend.app.database import AsyncSessionLocal
from vahannetra.backend.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_status = "up"
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            db_status = "down"

    status = "ok" if db_status == "up" else "degraded"
    return HealthResponse(status=status, database=db_status, redis="unknown")
