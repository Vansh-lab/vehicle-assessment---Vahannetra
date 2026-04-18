from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async
from app.database import get_async_db
from app.db_models import ClientErrorEvent, User

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class ClientErrorPayload(BaseModel):
    level: Literal["error", "warning"] = "error"
    message: str
    source: str | None = None
    stack: str | None = None
    route: str | None = None
    user_agent: str | None = None


@router.post("/client-error")
async def record_client_error(
    payload: ClientErrorPayload,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    event = ClientErrorEvent(
        organization_id=current_user.organization_id,
        level=payload.level,
        message=payload.message[:1000],
        source=(payload.source or "")[:255],
        stack=(payload.stack or "")[:10000],
        route=(payload.route or "")[:255],
        user_agent=(payload.user_agent or "")[:500],
    )
    db.add(event)
    await db.commit()
    return {"ok": True}
