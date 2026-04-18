import uuid
import json
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async, require_roles_async
from app.database import get_async_db
from app.db_models import Claim, Inspection, User
from app.services.connectors import IntegrationError, get_insurer_connector

router = APIRouter(tags=["operations"])
insurer_connector = get_insurer_connector()

SeverityLevel = Literal["low", "medium", "high"]
InspectionStatus = Literal["Completed", "Pending", "Failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class InspectionHistoryItem(BaseModel):
    id: str
    plate: str
    model: str
    date: str
    severity: SeverityLevel
    status: InspectionStatus
    risk_score: int


class FleetHealth(BaseModel):
    score: int
    attention_vehicles: int
    inspections_today: int
    active_alerts: int


class DashboardOverviewResponse(BaseModel):
    fleet_health: FleetHealth
    recent_inspections: list[InspectionHistoryItem]
    vehicles_requiring_attention: list[InspectionHistoryItem]


class ClaimSubmitRequest(BaseModel):
    inspection_id: str
    destination: str = Field(default="default-claims-provider")


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    inspection_id: str
    status: str
    provider_reference: str


def to_history_item(record: Inspection) -> InspectionHistoryItem:
    return InspectionHistoryItem(
        id=record.id,
        plate=record.plate,
        model=record.model,
        date=isoformat_utc_z(record.date),
        severity=record.severity,
        status=record.status,
        risk_score=record.risk_score,
    )


def _integration_error_contract(exc: IntegrationError) -> dict:
    try:
        parsed = json.loads(str(exc))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {
        "provider": "unknown",
        "code": "integration_error",
        "message": str(exc),
        "retryable": True,
    }


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(
        select(Inspection)
        .where(Inspection.organization_id == current_user.organization_id)
        .order_by(Inspection.date.desc())
    )
    all_items = result.scalars().all()
    recent = all_items[:10]
    attention = [item for item in all_items if item.severity in ("medium", "high")][:10]

    avg_health = (
        int(sum([item.health_score for item in all_items]) / len(all_items))
        if all_items
        else 100
    )
    health = FleetHealth(
        score=avg_health,
        attention_vehicles=len(attention),
        inspections_today=len(
            [item for item in all_items if item.date.date() == utc_now().date()]
        ),
        active_alerts=len([item for item in all_items if item.severity == "high"]),
    )

    return DashboardOverviewResponse(
        fleet_health=health,
        recent_inspections=[to_history_item(item) for item in recent],
        vehicles_requiring_attention=[to_history_item(item) for item in attention],
    )


@router.post("/claims/submit", response_model=ClaimSubmitResponse)
async def submit_claim(
    payload: ClaimSubmitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_roles_async("admin", "manager", "inspector")),
):
    inspection_result = await db.execute(
        select(Inspection).where(
            Inspection.id == payload.inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
    )
    inspection: Optional[Inspection] = inspection_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    claim_id = f"CLM-{uuid.uuid4().hex[:10].upper()}"
    claim_status = "Submitted"
    try:
        connector_response = await insurer_connector.submit_claim(
            inspection_id=inspection.id,
            destination=payload.destination,
            organization_id=current_user.organization_id,
        )
        provider_ref = connector_response.provider_reference
        claim_status = "Submitted" if connector_response.accepted else "Queued"
    except IntegrationError as exc:
        contract = _integration_error_contract(exc)
        provider = str(contract.get("provider", "connector")).upper()
        code = str(contract.get("code", "error")).upper()
        provider_ref = f"{provider}-{code}-PENDING-{uuid.uuid4().hex[:6]}"
        claim_status = "Queued"

    claim = Claim(
        id=claim_id,
        inspection_id=inspection.id,
        organization_id=current_user.organization_id,
        status=claim_status,
        provider_ref=provider_ref,
    )
    db.add(claim)
    await db.commit()

    return ClaimSubmitResponse(
        claim_id=claim_id,
        inspection_id=inspection.id,
        status=claim_status,
        provider_reference=provider_ref,
    )
