import os
import socket
import urllib.parse

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_async_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_url = os.getenv("REDIS_URL")
    redis_status = "not_configured"
    if redis_url:
        redis_status = "unavailable"
        try:
            parsed = urllib.parse.urlparse(redis_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            with socket.create_connection((host, port), timeout=0.5):
                redis_status = "up"
        except OSError:
            redis_status = "down"

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "redis": redis_status,
    }
