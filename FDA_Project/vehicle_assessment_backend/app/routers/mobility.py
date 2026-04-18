import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async
from app.database import get_async_db
from app.db_models import (
    Garage,
    Inspection,
    InspectionJob,
    InsuranceCenter,
    User,
    Vehicle,
)

router = APIRouter(prefix="/api/v1", tags=["mobility"])

MAX_PLATE_LENGTH = 12
MIN_VIN_LENGTH = 17
MARKET_AVG_PRICING = {
    "scratch": 3500,
    "dent": 8000,
    "paint": 6000,
    "major": 25000,
}


class V1VehicleCreateRequest(BaseModel):
    number_plate: str
    vin: Optional[str] = None
    vehicle_type: str = "4W"
    make: str = "Unknown"
    model: str = "Unknown"
    year: int = 2020
    fuel_type: str = "Petrol"
    is_ev: bool = False
    rto: str = "Unknown"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def smart_score(
    distance_km: float, rating: float, is_open: bool, services_count: int
) -> float:
    distance_component = 1 / max(distance_km, 0.1)
    return round(
        0.4 * distance_component
        + 0.3 * (rating / 5)
        + 0.2 * (1 if is_open else 0)
        + 0.1 * (services_count / 5),
        4,
    )


def market_verdict(delta_pct: int) -> str:
    if delta_pct <= -10:
        return "below_market"
    if delta_pct >= 10:
        return "above_market"
    return "market_rate"


def pricing_market_comparison(min_price: int, market_avg: int) -> dict:
    if market_avg <= 0:
        return {"market_avg": market_avg, "delta_pct": 0, "verdict": "market_rate"}
    delta_pct = int(round(((min_price - market_avg) / market_avg) * 100))
    return {
        "market_avg": market_avg,
        "delta_pct": delta_pct,
        "verdict": market_verdict(delta_pct),
    }


def price_badge(comparisons: dict[str, dict]) -> str:
    deltas = [item.get("delta_pct", 0) for item in comparisons.values()]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    if avg_delta <= -10:
        return "BELOW MARKET"
    if avg_delta >= 10:
        return "ABOVE MARKET"
    return "MARKET RATE"


def make_demo_vehicle(plate_or_vin: str) -> dict:
    catalog = [
        ("Maruti", "Baleno", "Petrol", False),
        ("Hyundai", "Creta", "Diesel", False),
        ("Tata", "Nexon EV", "Electric", True),
        ("Honda", "City", "Petrol", False),
        ("Mahindra", "XUV700", "Diesel", False),
    ]
    make, model, fuel_type, is_ev = random.choice(catalog)
    year = random.randint(2018, 2025)
    return {
        "number_plate": (
            plate_or_vin
            if len(plate_or_vin) <= MAX_PLATE_LENGTH
            else f"MH{random.randint(10, 50)}AB{random.randint(1000, 9999)}"
        ),
        "vin": (
            plate_or_vin
            if len(plate_or_vin) >= MIN_VIN_LENGTH
            else f"MA1{uuid.uuid4().hex[:14].upper()}"
        ),
        "vehicle_type": "4W",
        "make": make,
        "model": model,
        "year": year,
        "fuel_type": fuel_type,
        "is_ev": is_ev,
        "rto": random.choice(["MH12", "KA03", "DL01", "GJ05", "UP14"]),
        "rc_valid_until": isoformat_utc_z(
            utc_now() + timedelta(days=random.randint(250, 1400))
        ),
        "insurance_valid_until": isoformat_utc_z(
            utc_now() + timedelta(days=random.randint(60, 365))
        ),
        "previous_claim_count": random.randint(0, 3),
        "blacklist_status": "Not Blacklisted",
        "source": "VAHAN API (Demo)",
    }


@router.get("/results/{job_id}")
async def v1_results(
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(
        select(InspectionJob).where(
            InspectionJob.id == job_id,
            InspectionJob.organization_id == current_user.organization_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "input_type": job.input_type,
        "dsq_score": job.dsq_score,
        "overall_severity": job.overall_severity,
        "confidence_overall": job.confidence_overall,
        "fraud_risk_score": job.fraud_risk_score,
        "auto_approve": job.auto_approve,
        "repair_cost_min_inr": job.repair_cost_min_inr,
        "repair_cost_max_inr": job.repair_cost_max_inr,
        "dsq_breakdown": json.loads(job.dsq_breakdown or "{}"),
        "annotated_output": job.s3_annotated_key,
        "blockchain_hash": job.blockchain_hash,
    }


@router.get("/vehicles/lookup")
async def v1_vehicle_lookup(
    plate: Optional[str] = Query(default=None),
    vin: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    if not plate and not vin:
        raise HTTPException(status_code=400, detail="Provide plate or vin")
    normalized_plate = plate.upper() if plate else None

    query = select(Vehicle).where(
        Vehicle.organization_id == current_user.organization_id
    )
    if normalized_plate:
        query = query.where(Vehicle.number_plate == normalized_plate)
    if vin:
        query = query.where(Vehicle.vin.ilike(vin))

    result = await db.execute(query)
    record = result.scalars().first()
    if record:
        return {
            "id": record.id,
            "number_plate": record.number_plate,
            "vin": record.vin,
            "vehicle_type": record.vehicle_type,
            "make": record.make,
            "model": record.model,
            "year": record.year,
            "fuel_type": record.fuel_type,
            "is_ev": record.is_ev,
            "rto": record.rto,
            "rc_valid_until": isoformat_utc_z(record.rc_valid_until),
            "insurance_valid_until": isoformat_utc_z(record.insurance_valid_until),
            "previous_claim_count": record.previous_claim_count,
            "blacklist_status": record.blacklist_status,
            "source": "Database",
        }

    if os.getenv("VAHAN_API_KEY"):
        raise HTTPException(
            status_code=404, detail="Vehicle not found in local records"
        )
    return make_demo_vehicle(plate or vin or "UNKNOWN")


@router.post("/vehicles", status_code=201)
async def v1_create_vehicle(
    payload: V1VehicleCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    vehicle_id = f"VEH-{uuid.uuid4().hex[:10].upper()}"
    rc_valid_until = utc_now() + timedelta(days=365)
    insurance_valid_until = utc_now() + timedelta(days=200)

    vehicle = Vehicle(
        id=vehicle_id,
        organization_id=current_user.organization_id,
        number_plate=payload.number_plate.upper(),
        vin=payload.vin,
        vehicle_type=payload.vehicle_type,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        fuel_type=payload.fuel_type,
        is_ev=payload.is_ev,
        rto=payload.rto,
        rc_valid_until=rc_valid_until,
        insurance_valid_until=insurance_valid_until,
        vahan_data=json.dumps(payload.model_dump()),
        previous_claim_count=0,
        blacklist_status="Not Blacklisted",
    )
    db.add(vehicle)
    await db.commit()

    return {"id": vehicle_id, "status": "created"}


@router.get("/vehicles/{vehicle_id}/history")
async def v1_vehicle_history(
    vehicle_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    vehicle_result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == current_user.organization_id,
        )
    )
    vehicle = vehicle_result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    inspections_result = await db.execute(
        select(Inspection)
        .where(
            Inspection.organization_id == current_user.organization_id,
            (Inspection.plate == vehicle.number_plate)
            | (Inspection.vin == vehicle.vin),
        )
        .order_by(Inspection.date.desc())
    )
    inspections = inspections_result.scalars().all()

    return {
        "vehicle": {
            "id": vehicle.id,
            "number_plate": vehicle.number_plate,
            "vin": vehicle.vin,
            "make": vehicle.make,
            "model": vehicle.model,
        },
        "inspections": [
            {
                "inspection_id": item.id,
                "date": isoformat_utc_z(item.date),
                "severity": item.severity,
                "risk_score": item.risk_score,
                "health_score": item.health_score,
                "triage_category": item.triage_category,
            }
            for item in inspections
        ],
    }


@router.get("/garages/nearby")
async def v1_garages_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    sort: str = Query(default="smart_score"),
    damage_type: str = Query(default="dent"),
    ev_only: bool = Query(default=False),
    insurance_only: bool = Query(default=False),
    open_now: bool = Query(default=False),
    max_distance_km: float = Query(default=20.0),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    _ = current_user
    garages_result = await db.execute(select(Garage))
    garages = garages_result.scalars().all()

    enriched = []
    for garage in garages:
        if ev_only and not garage.is_ev_certified:
            continue
        if insurance_only and not garage.is_insurance_approved:
            continue
        if open_now and not garage.is_open_now:
            continue

        distance_km = haversine_km(lat, lng, garage.latitude, garage.longitude)
        if distance_km > max_distance_km:
            continue

        services = json.loads(garage.services or "[]")
        score = smart_score(
            distance_km, garage.rating, garage.is_open_now, len(services)
        )
        pricing = {
            "scratch": {
                "min": garage.pricing_scratch_min,
                "max": garage.pricing_scratch_max,
            },
            "dent": {"min": garage.pricing_dent_min, "max": garage.pricing_dent_max},
            "paint": {"min": garage.pricing_paint_min, "max": garage.pricing_paint_max},
            "major": {"min": garage.pricing_major_min, "max": garage.pricing_major_max},
        }
        market_comparison = {
            key: pricing_market_comparison(pricing[key]["min"], MARKET_AVG_PRICING[key])
            for key in ("scratch", "dent", "paint", "major")
        }

        enriched.append(
            {
                "id": garage.id,
                "name": garage.name,
                "address": garage.address,
                "city": garage.city,
                "phone": garage.phone,
                "latitude": garage.latitude,
                "longitude": garage.longitude,
                "distance_km": round(distance_km, 2),
                "rating": garage.rating,
                "is_open_now": garage.is_open_now,
                "services": services,
                "smart_score": score,
                "pricing": pricing,
                "market_comparison": market_comparison,
                "price_badge": price_badge(market_comparison),
                "hourly_labour_rate": garage.hourly_labour_rate,
                "workshop_type": garage.workshop_type,
                "certifications": json.loads(garage.certifications or "[]"),
                "years_in_business": garage.years_in_business,
                "google_maps_url": garage.google_maps_url,
            }
        )

    if sort == "distance":
        enriched.sort(key=lambda item: item["distance_km"])
    elif sort == "rating":
        enriched.sort(key=lambda item: item["rating"], reverse=True)
    elif sort == "cheapest":
        key = "major"
        damage = damage_type.lower()
        if "dent" in damage:
            key = "dent"
        elif "paint" in damage:
            key = "paint"
        elif "scratch" in damage:
            key = "scratch"
        enriched.sort(key=lambda item: item["pricing"][key]["min"])
    else:
        enriched.sort(key=lambda item: item["smart_score"], reverse=True)

    return {"items": enriched}


@router.get("/garages/insurance-centers")
async def v1_insurance_centers(
    lat: float = Query(...),
    lng: float = Query(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    _ = current_user
    centers_result = await db.execute(select(InsuranceCenter))
    centers = centers_result.scalars().all()

    items = []
    for center in centers:
        items.append(
            {
                "id": center.id,
                "name": center.name,
                "insurer_name": center.insurer_name,
                "address": center.address,
                "distance_km": round(
                    haversine_km(lat, lng, center.latitude, center.longitude), 2
                ),
                "phone": center.phone,
                "toll_free": center.toll_free,
                "rating": center.rating,
                "services": json.loads(center.services or "[]"),
                "cashless_network": center.cashless_network,
                "avg_claim_processing_days": center.avg_claim_processing_days,
                "cashless_garage_count": center.cashless_garage_count,
            }
        )

    items.sort(key=lambda item: item["distance_km"])
    return {"items": items}


@router.get("/garages/{garage_id}/pricing")
async def v1_garage_pricing(
    garage_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    _ = current_user
    garage_result = await db.execute(select(Garage).where(Garage.id == garage_id))
    garage = garage_result.scalar_one_or_none()
    if not garage:
        raise HTTPException(status_code=404, detail="Garage not found")

    return {
        "garage_id": garage.id,
        "name": garage.name,
        "pricing": {
            "scratch": {
                "min": garage.pricing_scratch_min,
                "max": garage.pricing_scratch_max,
            },
            "dent": {"min": garage.pricing_dent_min, "max": garage.pricing_dent_max},
            "paint": {"min": garage.pricing_paint_min, "max": garage.pricing_paint_max},
            "major": {"min": garage.pricing_major_min, "max": garage.pricing_major_max},
        },
        "hourly_labour_rate": garage.hourly_labour_rate,
    }
