import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async
from app.database import get_async_db
from app.db_models import Inspection, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/damage-distribution")
async def analytics_damage_distribution(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    inspections_result = await db.execute(
        select(Inspection).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    inspections = inspections_result.scalars().all()
    counts = {"scratch": 0, "dent": 0, "crack": 0, "broken part": 0, "paint damage": 0}

    for inspection in inspections:
        for item in json.loads(inspection.findings_json or "[]"):
            kind = item.get("type", "paint damage")
            if kind not in counts:
                kind = "paint damage"
            counts[kind] += 1

    return {
        "items": [{"category": key, "count": value} for key, value in counts.items()]
    }


@router.get("/severity-trends")
async def analytics_severity_trends(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    inspections_result = await db.execute(
        select(Inspection).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    inspections = inspections_result.scalars().all()
    bucket: dict[str, dict[str, int]] = {}
    for item in inspections:
        month = item.date.strftime("%b")
        if month not in bucket:
            bucket[month] = {"low": 0, "medium": 0, "high": 0}
        bucket[month][item.severity] += 1

    trends = [{"month": month, **counts} for month, counts in bucket.items()]
    return {"trends": trends}


@router.get("/vehicle-risk-ranking")
async def analytics_vehicle_risk_ranking(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    inspections_result = await db.execute(
        select(Inspection).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    inspections = inspections_result.scalars().all()
    score_by_model: dict[str, list[int]] = {}
    for item in inspections:
        score_by_model.setdefault(item.model, []).append(item.risk_score)

    ranking = [
        {"model": model, "risk": int(sum(scores) / len(scores))}
        for model, scores in score_by_model.items()
        if model
    ]
    ranking.sort(key=lambda entry: entry["risk"], reverse=True)
    return {"ranking": ranking}
