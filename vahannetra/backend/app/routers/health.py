from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from vahannetra.backend.app.database import AsyncSessionLocal
from vahannetra.backend.app.schemas import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_status = "up"
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db_status = "down"
            logger.exception("Phase2 backend health check failed for database.")

    status = "ok" if db_status == "up" else "degraded"
    return HealthResponse(status=status, database=db_status, redis="unknown")
