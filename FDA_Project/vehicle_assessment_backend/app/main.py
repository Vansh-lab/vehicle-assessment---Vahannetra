import json
import hmac
import hashlib
import math
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import engine
from app.db_models import (
    Garage,
    InsuranceCenter,
    Inspection,
    InspectionJob,
    Organization,
    Setting,
    User,
    Vehicle,
)
from app.core.settings import settings
from app.middleware.request_context import request_context_middleware
from app.routers.analytics import router as analytics_router
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.inspections import router as inspections_router
from app.routers.mobility import router as mobility_router
from app.routers.operations import router as operations_router
from app.routers.settings import router as settings_router
from app.routers.system import router as system_router
from app.routers.telemetry import router as telemetry_router
from app.routers.webhooks import router as webhooks_router
from app.secrets import get_secret
from app.services.detector import DamageDetector
from app.services.bootstrap import init_seed_data
from app.services.dsq_v2 import compute_dsq_v2
from app.services.storage import ArtifactStorageService

detector = DamageDetector()
storage_service = ArtifactStorageService()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SeverityLevel = Literal["low", "medium", "high"]
InspectionStatus = Literal["Completed", "Pending", "Failed"]
Theme = Literal["dark", "light"]
UserRole = Literal["admin", "manager", "inspector"]
MAX_PLATE_LENGTH = 12
MIN_VIN_LENGTH = 17


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class AuthLoginRequest(BaseModel):
    email: str
    password: str
    otp: Optional[str] = None


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class LogoutRequest(BaseModel):
    refresh_token: str


class VehicleSummary(BaseModel):
    plate: str
    model: str
    vin: Optional[str] = None
    type: Literal["Motorcycle", "Scooter", "3W", "4W"]
    inspected_at: str


class DamageFinding(BaseModel):
    id: str
    type: Literal["scratch", "dent", "crack", "broken part", "paint damage"]
    severity: SeverityLevel
    confidence: float
    category: Literal["Cosmetic", "Functional"]
    estimate_min: int
    estimate_max: int
    explainability: str
    box: list[float]


class InspectionHistoryItem(BaseModel):
    id: str
    plate: str
    model: str
    date: str
    severity: SeverityLevel
    status: InspectionStatus
    risk_score: int


class InspectionDetail(BaseModel):
    inspection_id: str
    vehicle: VehicleSummary
    health_score: int
    triage_category: Literal["COSMETIC", "STRUCTURAL/FUNCTIONAL"]
    processed_image_url: str
    findings: list[DamageFinding]


class FleetHealth(BaseModel):
    score: int
    attention_vehicles: int
    inspections_today: int
    active_alerts: int


class DashboardOverviewResponse(BaseModel):
    fleet_health: FleetHealth
    recent_inspections: list[InspectionHistoryItem]
    vehicles_requiring_attention: list[InspectionHistoryItem]


class NotificationPreferences(BaseModel):
    push: bool
    email: bool
    critical_only: bool


class OrganizationInfo(BaseModel):
    id: str
    name: str
    region: str
    active_inspectors: int


class SettingsResponse(BaseModel):
    organization: OrganizationInfo
    notifications: NotificationPreferences
    theme: Theme


class SettingsPatchRequest(BaseModel):
    theme: Optional[Theme] = None
    notifications: Optional[NotificationPreferences] = None


class ClaimSubmitRequest(BaseModel):
    inspection_id: str
    destination: str = Field(default="default-claims-provider")


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    inspection_id: str
    status: str
    provider_reference: str


class OtpDeliveryCallback(BaseModel):
    provider_message_id: str
    status: Literal["queued", "sent", "delivered", "failed", "bounced"]
    error_message: str | None = None
    payload: dict | None = None


class ClientErrorPayload(BaseModel):
    level: Literal["error", "warning"] = "error"
    message: str
    source: str | None = None
    stack: str | None = None
    route: str | None = None
    user_agent: str | None = None


class V1AnalyzeAccepted(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_seconds: int | None = None


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


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    issued_at: str
    user: dict
    organization: dict


def map_severity(score: float) -> SeverityLevel:
    if score > 70:
        return "high"
    if score > 35:
        return "medium"
    return "low"


def normalize_detection_type(raw_name: str) -> str:
    normalized = raw_name.lower()
    if normalized in {"scratch", "dent", "crack", "broken part", "paint damage"}:
        return normalized
    return "paint damage"


def extension_for_content_type(content_type: str | None, fallback: str = ".bin") -> str:
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if content_type == "video/mp4":
        return ".mp4"
    if content_type == "video/webm":
        return ".webm"
    return fallback


def finding_from_detection(
    index: int, det: dict, severity: SeverityLevel, triage_category: str
) -> DamageFinding:
    return DamageFinding(
        id=f"DMG-{index + 1}",
        type=normalize_detection_type(str(det.get("class", "paint damage"))),
        severity=severity,
        confidence=float(det.get("confidence", 0)),
        category="Cosmetic" if triage_category == "COSMETIC" else "Functional",
        estimate_min=(
            8000 if severity == "high" else 3000 if severity == "medium" else 1200
        ),
        estimate_max=(
            18000 if severity == "high" else 7000 if severity == "medium" else 2800
        ),
        explainability=f"Detected {det.get('class', 'damage')} based on contour/texture anomalies.",
        box=[float(x) for x in det.get("box", [0, 0, 0, 0])],
    )


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


MARKET_AVG_PRICING = {
    "scratch": 3500,
    "dent": 8000,
    "paint": 6000,
    "major": 25000,
}


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


def create_job_from_findings(
    db: Session,
    organization_id: str,
    findings: list[dict],
    input_type: str,
    annotated_key: str,
    image_keys: list[str] | None = None,
    video_key: str = "",
    status: str = "completed",
) -> InspectionJob:
    dsq_result = compute_dsq_v2(findings, (720, 1280, 3))
    score = dsq_result.score
    severity = dsq_result.overall_severity
    hash_payload = f"{organization_id}:{score}:{utc_now().isoformat()}"
    hash_secret_key = (
        get_secret("VAHANNETRA_HASH_SECRET", "vahannetra-hash-secret") or ""
    ).encode("utf-8")
    hash_value = hmac.new(
        hash_secret_key, hash_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    job = InspectionJob(
        id=f"JOB-{uuid.uuid4().hex[:12].upper()}",
        organization_id=organization_id,
        status=status,
        input_type=input_type,
        s3_image_keys=json.dumps(image_keys or []),
        s3_video_key=video_key,
        s3_annotated_key=annotated_key,
        dsq_score=round(score, 2),
        dsq_breakdown=json.dumps(dsq_result.breakdown),
        overall_severity=severity,
        confidence_overall=round(
            max([float(item.get("confidence", 0.0)) for item in findings], default=0.0),
            4,
        ),
        fraud_risk_score=dsq_result.fraud_risk_score,
        fraud_flags=json.dumps([]),
        auto_approve=dsq_result.auto_approve,
        repair_cost_min_inr=dsq_result.repair_cost_min_inr,
        repair_cost_max_inr=dsq_result.repair_cost_max_inr,
        recommendation="Proceed with repair estimate and insurer review.",
        insurance_claim_steps="Upload RC, policy, and inspection images. Submit claim and await surveyor review.",
        blockchain_hash=hash_value,
        completed_at=utc_now() if status == "completed" else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def validate_upload(file: UploadFile, payload: bytes) -> None:
    max_size_bytes = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(8 * 1024 * 1024)))
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(payload) > max_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail="Only JPEG, PNG and WEBP files are allowed"
        )

    header = payload[:12]
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(status_code=400, detail="Invalid image signature")

    decoded = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(
            status_code=400, detail="Corrupt or unsupported image payload"
        )


def validate_video_upload(file: UploadFile, payload: bytes) -> None:
    allowed_types = {"video/mp4", "video/webm", "video/quicktime", "video/mov"}
    max_size_bytes = int(
        os.getenv("MAX_VIDEO_UPLOAD_SIZE_BYTES", str(100 * 1024 * 1024))
    )
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded video is empty")
    if len(payload) > max_size_bytes:
        raise HTTPException(status_code=413, detail="Video exceeds max size of 100MB")
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail="Only mp4, webm and mov video files are allowed"
        )


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


def to_inspection_detail(record: Inspection) -> InspectionDetail:
    findings_payload = json.loads(record.findings_json or "[]")
    findings = [DamageFinding(**item) for item in findings_payload]
    return InspectionDetail(
        inspection_id=record.id,
        vehicle=VehicleSummary(
            plate=record.plate,
            model=record.model,
            vin=record.vin,
            type=record.vehicle_type,
            inspected_at=isoformat_utc_z(record.date),
        ),
        health_score=record.health_score,
        triage_category=record.triage_category,
        processed_image_url=record.processed_image_url,
        findings=findings,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_seed_data()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none';"
    )
    return response


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    return await request_context_middleware(request, call_next)


@app.get("/")
async def root():
    return {"message": "AI Vehicle Assessment API is running", "docs": "/docs"}


app.include_router(system_router)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)
app.include_router(mobility_router)
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(settings_router)
app.include_router(inspections_router)
app.include_router(telemetry_router)
app.include_router(analyze_router)
app.include_router(operations_router)
