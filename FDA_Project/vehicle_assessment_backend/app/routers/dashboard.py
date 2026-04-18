from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_async_db
from app.db_models import Inspection, InspectionJob, User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def v1_dashboard_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    inspections_result = await db.execute(
        select(Inspection).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    jobs_result = await db.execute(
        select(InspectionJob).where(
            InspectionJob.organization_id == current_user.organization_id
        )
    )
    inspections = inspections_result.scalars().all()
    jobs = jobs_result.scalars().all()

    total = len(inspections)
    completed = len([item for item in inspections if item.status == "Completed"])
    auto_approved = len([item for item in jobs if item.auto_approve])
    avg_dsq = (
        round(sum([item.dsq_score for item in jobs]) / len(jobs), 2) if jobs else 0.0
    )
    fraud_rate = (
        round(
            (len([item for item in jobs if item.fraud_risk_score > 60]) / len(jobs))
            * 100,
            2,
        )
        if jobs
        else 0.0
    )

    return {
        "total_inspections": total,
        "completion_rate": round((completed / total) * 100, 2) if total else 0.0,
        "auto_approved": auto_approved,
        "avg_dsq": avg_dsq,
        "avg_inference_ms": 1200,
        "fraud_rate": fraud_rate,
    }


@router.get("/timeline")
async def v1_dashboard_timeline(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    inspections_result = await db.execute(
        select(Inspection.date).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    inspection_dates = inspections_result.scalars().all()

    today = datetime.now(timezone.utc).date()
    bucket: dict[str, int] = {}
    for offset in range(days):
        date_key = (today - timedelta(days=offset)).isoformat()
        bucket[date_key] = 0

    for inspection_date in inspection_dates:
        key = inspection_date.date().isoformat()
        if key in bucket:
            bucket[key] += 1

    items = [
        {"date": date_key, "count": bucket[date_key]}
        for date_key in sorted(bucket.keys())
    ]
    return {"items": items}
