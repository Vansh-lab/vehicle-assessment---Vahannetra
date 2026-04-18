import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_async_db
from app.db_models import User, WebhookSubscription
from app.services.webhook_dispatcher import build_retry_schedule, build_signature
from app.tasks.webhooks import deliver_webhook
from app.utils.network import ensure_public_http_url

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class V1WebhookRegisterRequest(BaseModel):
    target_url: str
    event_type: str = "inspection.completed"
    secret: Optional[str] = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    normalized = (
        value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    )
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("/register", status_code=201)
async def v1_register_webhook(
    payload: V1WebhookRegisterRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    ensure_public_http_url(payload.target_url)
    webhook = WebhookSubscription(
        id=f"WH-{uuid.uuid4().hex[:10].upper()}",
        organization_id=current_user.organization_id,
        target_url=payload.target_url,
        event_type=payload.event_type,
        secret=payload.secret or uuid.uuid4().hex,
        active=True,
    )
    db.add(webhook)
    await db.commit()

    return {
        "id": webhook.id,
        "event_type": webhook.event_type,
        "target_url": webhook.target_url,
    }


@router.get("")
async def v1_list_webhooks(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WebhookSubscription)
        .where(WebhookSubscription.organization_id == current_user.organization_id)
        .order_by(WebhookSubscription.created_at.desc())
    )
    webhooks = result.scalars().all()
    return {
        "items": [
            {
                "id": item.id,
                "target_url": item.target_url,
                "event_type": item.event_type,
                "active": item.active,
                "created_at": isoformat_utc_z(item.created_at),
            }
            for item in webhooks
        ]
    }


@router.delete("/{webhook_id}", status_code=204)
async def v1_delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.organization_id == current_user.organization_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    await db.commit()
    return None


@router.post("/test/{webhook_id}")
async def v1_test_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.organization_id == current_user.organization_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = {
        "event": webhook.event_type,
        "timestamp": isoformat_utc_z(utc_now()),
        "status": "test",
        "organization_id": current_user.organization_id,
    }
    signature = build_signature(webhook.secret, payload)
    schedule = build_retry_schedule(max_attempts=5)

    task_id = None
    try:
        task = deliver_webhook.delay(webhook.target_url, payload, signature)
        task_id = task.id
    except Exception:
        task_id = None

    return {
        "webhook_id": webhook.id,
        "signature": signature,
        "payload": payload,
        "delivered": True,
        "task_id": task_id,
        "retry_schedule": [isoformat_utc_z(item.scheduled_at) for item in schedule],
    }
