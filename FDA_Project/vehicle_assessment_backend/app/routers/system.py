from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async
from app.core.settings import settings
from app.database import get_async_db
from app.db_models import User, WebhookDeadLetter
from app.tasks.pipeline import PIPELINE_STEPS

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/capabilities")
def capabilities():
    return {
        "app_name": settings.app_name,
        "pipeline_steps": PIPELINE_STEPS,
        "storage_bucket": settings.s3_bucket,
        "queue": settings.celery_queue,
        "queue_dlq": settings.celery_dlq_queue,
        "celery": {
            "visibility_timeout_seconds": settings.celery_visibility_timeout_seconds,
            "soft_time_limit_seconds": settings.celery_soft_time_limit_seconds,
            "hard_time_limit_seconds": settings.celery_hard_time_limit_seconds,
        },
        "integrations": {
            "mode": settings.integration_mode,
            "timeout_seconds": settings.integration_timeout_seconds,
            "max_retries": settings.integration_max_retries,
            "circuit_failures": settings.integration_circuit_failures,
            "circuit_recovery_seconds": settings.integration_circuit_recovery_seconds,
        },
    }


@router.get("/queue/observability")
async def queue_observability(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    base = select(func.count(WebhookDeadLetter.id)).where(
        WebhookDeadLetter.organization_id == current_user.organization_id
    )
    open_count = (
        await db.execute(base.where(WebhookDeadLetter.status == "open"))
    ).scalar_one()
    resolved_count = (
        await db.execute(base.where(WebhookDeadLetter.status == "resolved"))
    ).scalar_one()
    requeued_count = (
        await db.execute(base.where(WebhookDeadLetter.status == "requeued"))
    ).scalar_one()
    sla_minutes = 30
    open_rows = (
        await db.execute(
            select(WebhookDeadLetter.created_at).where(
                WebhookDeadLetter.organization_id == current_user.organization_id,
                WebhookDeadLetter.status == "open",
            )
        )
    ).all()
    now = datetime.now(timezone.utc)
    overdue_count = 0
    for row in open_rows:
        created_at = row[0]
        if created_at is None:
            continue
        normalized = (
            created_at
            if created_at.tzinfo is not None
            else created_at.replace(tzinfo=timezone.utc)
        )
        if (now - normalized).total_seconds() > sla_minutes * 60:
            overdue_count += 1
    return {
        "queue": settings.celery_queue,
        "queue_dlq": settings.celery_dlq_queue,
        "dlq_open": open_count,
        "dlq_resolved": resolved_count,
        "dlq_requeued": requeued_count,
        "sla_minutes": sla_minutes,
        "sla_overdue_open": overdue_count,
        "escalation_required": overdue_count > 0,
    }
