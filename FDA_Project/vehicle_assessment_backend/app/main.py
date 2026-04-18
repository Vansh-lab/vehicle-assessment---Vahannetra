import json
import hmac
import hashlib
import math
import os
import random
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_refresh_token,
    exchange_refresh_token,
    get_current_user,
    hash_password,
    hash_secret,
    require_roles,
    verify_password,
)
from app.database import Base, apply_rls_policies, engine, get_db
from app.db_models import (
    Claim,
    ClientErrorEvent,
    Garage,
    InsuranceCenter,
    Inspection,
    InspectionJob,
    Organization,
    OtpCode,
    OtpDeliveryEvent,
    RefreshToken,
    Setting,
    User,
    Vehicle,
)
from app.otp_provider import get_otp_provider
from app.pdf_reports import render_inspection_report
from app.core.settings import settings
from app.middleware.request_context import request_context_middleware
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.system import router as system_router
from app.routers.webhooks import router as webhooks_router
from app.secrets import get_secret
from app.services.detector import DamageDetector
from app.services.dsq_v2 import compute_dsq_v2
from app.services.storage import ArtifactStorageService
from app.services.video_processing import extract_best_frames
from app.utils.assessment import calculate_dsi
from app.utils.network import ensure_public_http_url

detector = DamageDetector()
otp_provider = get_otp_provider()
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


def issue_token_bundle(
    db: Session, user: User, organization: Organization
) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(db, user),
        issued_at=isoformat_utc_z(utc_now()),
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        organization={
            "id": organization.id,
            "name": organization.name,
            "region": organization.region,
        },
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


def init_seed_data() -> None:
    Base.metadata.create_all(bind=engine)
    apply_rls_policies()
    db = next(get_db())
    try:
        org = db.query(Organization).filter(Organization.id == "org_001").first()
        if not org:
            org = Organization(
                id="org_001",
                name="Acme Claims Pvt Ltd",
                region="Mumbai",
                active_inspectors=42,
            )
            db.add(org)
            db.commit()

        if not db.query(User).filter(User.email == "ops@insurer.com").first():
            admin = User(
                id="usr_001",
                email="ops@insurer.com",
                name="Field Inspector",
                role="admin",
                password_hash=hash_password("password123"),
                organization_id=org.id,
            )
            db.add(admin)

        if not db.query(Setting).filter(Setting.organization_id == org.id).first():
            db.add(
                Setting(
                    organization_id=org.id,
                    push=True,
                    email=True,
                    critical_only=False,
                    theme="dark",
                )
            )

        if db.query(Inspection).count() == 0:
            sample_inspections = [
                Inspection(
                    id="INSP-1021",
                    organization_id=org.id,
                    plate="MH12AB9087",
                    model="Hyundai i20",
                    vin="MA3EHKD17A1234567",
                    vehicle_type="4W",
                    date=utc_now() - timedelta(hours=8),
                    severity="medium",
                    status="Completed",
                    risk_score=58,
                    health_score=63,
                    triage_category="STRUCTURAL/FUNCTIONAL",
                    processed_image_url="uploads/Sample2_Image_detected.jpg",
                    findings_json=json.dumps(
                        [
                            DamageFinding(
                                id="DMG-1",
                                type="dent",
                                severity="high",
                                confidence=0.93,
                                category="Functional",
                                estimate_min=8500,
                                estimate_max=14000,
                                explainability="Panel deformation and contour discontinuity suggest high impact dent.",
                                box=[40, 80, 210, 220],
                            ).model_dump(),
                            DamageFinding(
                                id="DMG-2",
                                type="scratch",
                                severity="medium",
                                confidence=0.88,
                                category="Cosmetic",
                                estimate_min=2500,
                                estimate_max=4900,
                                explainability="Linear surface discontinuity indicates layered paint damage.",
                                box=[250, 120, 390, 195],
                            ).model_dump(),
                        ]
                    ),
                ),
                Inspection(
                    id="INSP-1022",
                    organization_id=org.id,
                    plate="DL3CB7781",
                    model="Honda Activa",
                    vehicle_type="Scooter",
                    date=utc_now() - timedelta(hours=6),
                    severity="low",
                    status="Completed",
                    risk_score=31,
                    health_score=86,
                    triage_category="COSMETIC",
                    processed_image_url="uploads/Sample_Image_detected.jpg",
                    findings_json="[]",
                ),
                Inspection(
                    id="INSP-1023",
                    organization_id=org.id,
                    plate="KA05MN2211",
                    model="Tata Nexon",
                    vehicle_type="4W",
                    date=utc_now() - timedelta(hours=4),
                    severity="high",
                    status="Completed",
                    risk_score=84,
                    health_score=42,
                    triage_category="STRUCTURAL/FUNCTIONAL",
                    processed_image_url="uploads/Sample3_Image_detected.jpg",
                    findings_json="[]",
                ),
            ]
            for item in sample_inspections:
                db.add(item)

        if db.query(Vehicle).count() == 0:
            demo = make_demo_vehicle("MH12AB9087")
            db.add(
                Vehicle(
                    id=f"VEH-{uuid.uuid4().hex[:10].upper()}",
                    organization_id=org.id,
                    number_plate=demo["number_plate"],
                    vin=demo["vin"],
                    vehicle_type=demo["vehicle_type"],
                    make=demo["make"],
                    model=demo["model"],
                    year=demo["year"],
                    fuel_type=demo["fuel_type"],
                    is_ev=demo["is_ev"],
                    rto=demo["rto"],
                    rc_valid_until=ensure_utc(
                        datetime.fromisoformat(
                            demo["rc_valid_until"].replace("Z", "+00:00")
                        )
                    ),
                    insurance_valid_until=ensure_utc(
                        datetime.fromisoformat(
                            demo["insurance_valid_until"].replace("Z", "+00:00")
                        )
                    ),
                    vahan_data=json.dumps(demo),
                    previous_claim_count=demo["previous_claim_count"],
                    blacklist_status=demo["blacklist_status"],
                )
            )

        if db.query(Garage).count() == 0:
            garages = [
                Garage(
                    id="GAR-MUM-001",
                    name="Prime Auto Works",
                    address="Andheri East, Mumbai",
                    city="Mumbai",
                    state="Maharashtra",
                    pincode="400069",
                    phone="+91-9876500001",
                    latitude=19.1136,
                    longitude=72.8697,
                    rating=4.6,
                    is_open_now=True,
                    services=json.dumps(
                        ["Dent repair", "Paint booth", "Insurance approved"]
                    ),
                    is_insurance_approved=True,
                    is_ev_certified=True,
                    google_maps_url="https://maps.google.com",
                    pricing_dent_min=5000,
                    pricing_dent_max=9000,
                    pricing_scratch_min=2000,
                    pricing_scratch_max=4000,
                    pricing_paint_min=4000,
                    pricing_paint_max=8000,
                    pricing_major_min=15000,
                    pricing_major_max=30000,
                    hourly_labour_rate=1200,
                    workshop_type="authorized",
                    certifications=json.dumps(["ISO 9001", "MSME"]),
                    years_in_business=12,
                ),
                Garage(
                    id="GAR-MUM-002",
                    name="Budget Car Care",
                    address="Powai, Mumbai",
                    city="Mumbai",
                    state="Maharashtra",
                    pincode="400076",
                    phone="+91-9876500002",
                    latitude=19.1183,
                    longitude=72.9052,
                    rating=4.3,
                    is_open_now=True,
                    services=json.dumps(
                        ["Dent repair", "Scratch removal", "EV certified"]
                    ),
                    is_insurance_approved=False,
                    is_ev_certified=True,
                    google_maps_url="https://maps.google.com",
                    pricing_dent_min=4500,
                    pricing_dent_max=8200,
                    pricing_scratch_min=1800,
                    pricing_scratch_max=3600,
                    pricing_paint_min=3800,
                    pricing_paint_max=7600,
                    pricing_major_min=13000,
                    pricing_major_max=28000,
                    hourly_labour_rate=980,
                    workshop_type="multi-brand",
                    certifications=json.dumps(["GoMechanic Partner"]),
                    years_in_business=8,
                ),
            ]
            for garage in garages:
                db.add(garage)

        if db.query(InsuranceCenter).count() == 0:
            db.add(
                InsuranceCenter(
                    id="INS-MUM-001",
                    name="Horizon Claims Desk",
                    insurer_name="Horizon General Insurance",
                    address="Bandra Kurla Complex, Mumbai",
                    city="Mumbai",
                    phone="+91-1800-123-900",
                    toll_free="1800-123-900",
                    latitude=19.0707,
                    longitude=72.8697,
                    rating=4.2,
                    services=json.dumps(["Claim registration", "Cashless support"]),
                    cashless_network=True,
                    avg_claim_processing_days=6,
                    cashless_garage_count=128,
                )
            )

        db.commit()
    finally:
        db.close()


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


@app.post("/auth/login", response_model=AuthResponse)
async def auth_login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    organization = (
        db.query(Organization).filter(Organization.id == user.organization_id).first()
    )
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")

    return issue_token_bundle(db, user, organization)


@app.post("/auth/refresh", response_model=AuthResponse)
async def auth_refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)):
    user = exchange_refresh_token(db, payload.refresh_token)
    organization = (
        db.query(Organization).filter(Organization.id == user.organization_id).first()
    )
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")
    return issue_token_bundle(db, user, organization)


@app.post("/auth/logout")
async def auth_logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    token_hash = hash_secret(payload.refresh_token)
    token_record = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )
    if token_record:
        token_record.revoked = True
        db.commit()
    return {"message": "Logged out"}


@app.post("/auth/forgot-password")
async def auth_forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        return {
            "message": "If this email exists, an OTP has been sent",
            "otp_required": True,
            "channel": "email",
        }

    otp_code = str(random.randint(100000, 999999))
    db.add(
        OtpCode(
            email=user.email,
            code_hash=hash_secret(otp_code),
            purpose="forgot_password",
            expires_at=utc_now() + timedelta(minutes=10),
            used=False,
        )
    )
    db.commit()

    delivery_event = OtpDeliveryEvent(
        email=user.email, organization_id=user.organization_id, status="pending"
    )
    db.add(delivery_event)
    db.commit()
    db.refresh(delivery_event)

    send_result = otp_provider.send_otp(user.email, otp_code)
    delivery_event.provider = send_result.provider
    delivery_event.provider_message_id = send_result.provider_message_id
    delivery_event.status = send_result.status
    delivery_event.attempts = send_result.attempts
    delivery_event.error_message = send_result.error_message
    db.commit()
    return {
        "message": f"OTP sent to {user.email}",
        "otp_required": True,
        "channel": "email",
    }


@app.post("/auth/verify-otp", response_model=AuthResponse)
async def auth_verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    otp_record = (
        db.query(OtpCode)
        .filter(
            OtpCode.email == user.email,
            OtpCode.purpose == "forgot_password",
            OtpCode.used.is_(False),
        )
        .order_by(OtpCode.id.desc())
        .first()
    )
    if (
        not otp_record
        or ensure_utc(otp_record.expires_at) < utc_now()
        or otp_record.code_hash != hash_secret(payload.otp)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    otp_record.used = True
    db.commit()

    organization = (
        db.query(Organization).filter(Organization.id == user.organization_id).first()
    )
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")

    return issue_token_bundle(db, user, organization)


@app.post("/auth/otp/delivery-callback")
async def auth_otp_delivery_callback(
    payload: OtpDeliveryCallback,
    request: Request,
    db: Session = Depends(get_db),
):
    callback_secret = get_secret("OTP_CALLBACK_SECRET", "dev-callback-secret")
    provided = request.headers.get("X-Callback-Secret")
    if not provided or not hmac.compare_digest(provided, callback_secret):
        raise HTTPException(status_code=401, detail="Invalid callback secret")

    event = (
        db.query(OtpDeliveryEvent)
        .filter(OtpDeliveryEvent.provider_message_id == payload.provider_message_id)
        .order_by(OtpDeliveryEvent.id.desc())
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Delivery event not found")

    event.status = payload.status
    event.error_message = payload.error_message or ""
    event.callback_payload = json.dumps(payload.payload or {})
    db.commit()
    return {"ok": True}


@app.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_items = (
        db.query(Inspection)
        .filter(Inspection.organization_id == current_user.organization_id)
        .order_by(Inspection.date.desc())
        .all()
    )
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


@app.post("/assess-damage/")
async def assess_damage(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = await file.read()
    validate_upload(file, payload)

    base_name = Path(file.filename or "upload").name
    sanitized_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    safe_name = f"{uuid.uuid4().hex}_{sanitized_name}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as output_file:
        output_file.write(payload)

    raw_detections, processed_img_path = detector.analyze_vehicle(str(file_path))

    image = cv2.imread(str(file_path))
    dsi_score = calculate_dsi(raw_detections, image.shape) if image is not None else 0
    triage_category = "COSMETIC" if dsi_score < 40 else "STRUCTURAL/FUNCTIONAL"
    severity = map_severity(dsi_score)

    finding_models = [
        finding_from_detection(
            index=index, det=det, severity=severity, triage_category=triage_category
        )
        for index, det in enumerate(raw_detections)
    ]

    inspection_id = f"INSP-{int(utc_now().timestamp())}-{uuid.uuid4().hex[:6]}"
    inspection = Inspection(
        id=inspection_id,
        organization_id=current_user.organization_id,
        plate="Unknown",
        model="Unknown",
        vin=None,
        vehicle_type="4W",
        date=utc_now(),
        severity=severity,
        status="Completed",
        risk_score=min(100, int(dsi_score)),
        health_score=max(0, 100 - int(dsi_score)),
        triage_category=triage_category,
        processed_image_url=f"uploads/{Path(processed_img_path).name}",
        findings_json=json.dumps([finding.model_dump() for finding in finding_models]),
    )
    db.add(inspection)
    db.commit()

    return {
        "inspection_summary": {
            "dsi_score": dsi_score,
            "overall_severity": "High" if dsi_score > 60 else "Moderate",
            "triage_category": triage_category,
        },
        "inspection_id": inspection_id,
        "processed_image_url": f"uploads/{Path(processed_img_path).name}",
        "findings": raw_detections,
    }


@app.get("/view-result/{filename}")
async def get_result_image(
    filename: str, current_user: User = Depends(get_current_user)
):
    _ = current_user
    if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = next(
        (
            candidate
            for candidate in UPLOAD_DIR.iterdir()
            if candidate.is_file() and candidate.name == filename
        ),
        None,
    )

    if file_path:
        return FileResponse(file_path.resolve())
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/inspections", response_model=list[InspectionHistoryItem])
async def list_inspections(
    search: Optional[str] = Query(default=None),
    severity: Optional[SeverityLevel] = Query(default=None),
    status: Optional[InspectionStatus] = Query(default=None),
    date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Inspection).filter(
        Inspection.organization_id == current_user.organization_id
    )

    if search:
        search_value = f"%{search.lower()}%"
        query = query.filter(
            (Inspection.plate.ilike(search_value))
            | (Inspection.model.ilike(search_value))
        )

    if severity:
        query = query.filter(Inspection.severity == severity)

    if status:
        query = query.filter(Inspection.status == status)

    records = query.order_by(Inspection.date.desc()).all()
    if date:
        records = [item for item in records if item.date.date().isoformat() == date]

    return [to_history_item(item) for item in records]


@app.get("/inspections/{inspection_id}", response_model=InspectionDetail)
async def get_inspection_detail(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(Inspection)
        .filter(
            Inspection.id == inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return to_inspection_detail(record)


@app.get("/inspections/{inspection_id}/report.pdf")
async def download_report(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(Inspection)
        .filter(
            Inspection.id == inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found")

    detail = to_inspection_detail(record)
    pdf_bytes = render_inspection_report(
        {
            "inspection_id": detail.inspection_id,
            "vehicle": detail.vehicle.model_dump(),
            "health_score": detail.health_score,
            "triage_category": detail.triage_category,
            "findings": [item.model_dump() for item in detail.findings],
        }
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{inspection_id}.pdf"',
            "X-Report-Signature": hash_secret(
                inspection_id + str(record.date.timestamp())
            ),
        },
    )


@app.post("/claims/submit", response_model=ClaimSubmitResponse)
async def submit_claim(
    payload: ClaimSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "inspector")),
):
    inspection = (
        db.query(Inspection)
        .filter(
            Inspection.id == payload.inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    claim_id = f"CLM-{uuid.uuid4().hex[:10].upper()}"
    provider_ref = f"{payload.destination.upper()}-{uuid.uuid4().hex[:8]}"
    claim = Claim(
        id=claim_id,
        inspection_id=inspection.id,
        organization_id=current_user.organization_id,
        status="Submitted",
        provider_ref=provider_ref,
    )
    db.add(claim)
    db.commit()

    return ClaimSubmitResponse(
        claim_id=claim_id,
        inspection_id=inspection.id,
        status="Submitted",
        provider_reference=provider_ref,
    )


@app.get("/analytics/damage-distribution")
async def analytics_damage_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspections = (
        db.query(Inspection)
        .filter(Inspection.organization_id == current_user.organization_id)
        .all()
    )
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


@app.get("/analytics/severity-trends")
async def analytics_severity_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspections = (
        db.query(Inspection)
        .filter(Inspection.organization_id == current_user.organization_id)
        .all()
    )
    bucket: dict[str, dict[str, int]] = {}
    for item in inspections:
        month = item.date.strftime("%b")
        if month not in bucket:
            bucket[month] = {"low": 0, "medium": 0, "high": 0}
        bucket[month][item.severity] += 1

    trends = [{"month": month, **counts} for month, counts in bucket.items()]
    return {"trends": trends}


@app.get("/analytics/vehicle-risk-ranking")
async def analytics_vehicle_risk_ranking(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspections = (
        db.query(Inspection)
        .filter(Inspection.organization_id == current_user.organization_id)
        .all()
    )
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


@app.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    setting = (
        db.query(Setting)
        .filter(Setting.organization_id == current_user.organization_id)
        .first()
    )
    if not org or not setting:
        raise HTTPException(status_code=404, detail="Settings not found")

    return SettingsResponse(
        organization=OrganizationInfo(
            id=org.id,
            name=org.name,
            region=org.region,
            active_inspectors=org.active_inspectors,
        ),
        notifications=NotificationPreferences(
            push=setting.push, email=setting.email, critical_only=setting.critical_only
        ),
        theme=setting.theme,
    )


@app.patch("/settings", response_model=SettingsResponse)
async def patch_settings(
    payload: SettingsPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    setting = (
        db.query(Setting)
        .filter(Setting.organization_id == current_user.organization_id)
        .first()
    )
    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if not setting or not org:
        raise HTTPException(status_code=404, detail="Settings not found")

    if payload.theme is not None:
        setting.theme = payload.theme

    if payload.notifications is not None:
        setting.push = payload.notifications.push
        setting.email = payload.notifications.email
        setting.critical_only = payload.notifications.critical_only

    db.commit()
    db.refresh(setting)

    return SettingsResponse(
        organization=OrganizationInfo(
            id=org.id,
            name=org.name,
            region=org.region,
            active_inspectors=org.active_inspectors,
        ),
        notifications=NotificationPreferences(
            push=setting.push, email=setting.email, critical_only=setting.critical_only
        ),
        theme=setting.theme,
    )


@app.post("/telemetry/client-error")
async def record_client_error(
    payload: ClientErrorPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    db.commit()
    return {"ok": True}


@app.post("/api/v1/analyze", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(files) < 1 or len(files) > 10:
        raise HTTPException(status_code=400, detail="Upload between 1 and 10 images")

    detections: list[dict] = []
    image_keys: list[str] = []
    annotated = ""
    for index, file in enumerate(files):
        payload = await file.read()
        validate_upload(file, payload)
        safe_name = f"img_{uuid.uuid4().hex}{extension_for_content_type(file.content_type, fallback='.jpg')}"
        file_path = UPLOAD_DIR / safe_name
        with open(file_path, "wb") as output_file:
            output_file.write(payload)
        image_keys.append(f"uploads/{safe_name}")
        if index == 0:
            detections, processed_img_path = detector.analyze_vehicle(str(file_path))
            annotated = f"uploads/{Path(processed_img_path).name}"

    job = create_job_from_findings(
        db,
        current_user.organization_id,
        detections,
        input_type="multi" if len(files) > 1 else "photo",
        annotated_key=annotated,
        image_keys=image_keys,
        status="completed",
    )
    return V1AnalyzeAccepted(
        job_id=job.id, status="queued", message="Analysis accepted"
    )


@app.post("/api/v1/analyze/url", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze_url(
    image_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_public_http_url(image_url)

    job = create_job_from_findings(
        db,
        current_user.organization_id,
        [],
        input_type="photo",
        annotated_key="",
        image_keys=[image_url],
        status="queued",
    )
    return V1AnalyzeAccepted(
        job_id=job.id, status="queued", message="URL analysis accepted"
    )


@app.post("/api/v1/analyze/video", status_code=202, response_model=V1AnalyzeAccepted)
async def v1_analyze_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = await file.read()
    validate_video_upload(file, payload)

    job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
    safe_name = f"{job_id}_input{extension_for_content_type(file.content_type, fallback='.webm')}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as output_file:
        output_file.write(payload)

    frames_dir = UPLOAD_DIR / f"{job_id}_frames"
    extraction = extract_best_frames(
        file_path, frames_dir, n_frames=6, sharpness_threshold=100.0
    )
    estimated_seconds = max(3, min(120, extraction.duration_seconds + 4))

    frame_keys: list[str] = []
    detections: list[dict] = []
    annotated_output = ""
    for index, frame in enumerate(extraction.extracted_frames, start=1):
        frame_key = f"jobs/{job_id}/frame_{index}.jpg"
        frame_keys.append(frame_key)
        try:
            with open(frame.frame_path, "rb") as frame_file:
                await storage_service.upload_bytes(
                    frame_key, frame_file.read(), "image/jpeg"
                )
        except OSError:
            pass

        frame_detections, frame_annotated_path = detector.analyze_vehicle(
            str(frame.frame_path)
        )
        detections.extend(frame_detections)
        if not annotated_output and frame_annotated_path:
            annotated_output = frame_annotated_path

    video_key = f"jobs/{job_id}/input_video{extension_for_content_type(file.content_type, fallback='.webm')}"
    await storage_service.upload_bytes(
        video_key, payload, file.content_type or "video/webm"
    )

    if annotated_output:
        try:
            with open(annotated_output, "rb") as annotated_file:
                await storage_service.upload_bytes(
                    f"jobs/{job_id}/annotated.jpg",
                    annotated_file.read(),
                    "image/jpeg",
                )
        except OSError:
            pass

    job = create_job_from_findings(
        db,
        current_user.organization_id,
        detections,
        input_type="video",
        annotated_key=f"jobs/{job_id}/annotated.jpg" if annotated_output else "",
        image_keys=frame_keys,
        video_key=video_key,
        status="completed",
    )
    return V1AnalyzeAccepted(
        job_id=job.id,
        status="queued",
        message="Video analysis accepted",
        estimated_seconds=estimated_seconds,
    )


@app.get("/api/v1/results/{job_id}")
async def v1_results(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(InspectionJob)
        .filter(
            InspectionJob.id == job_id,
            InspectionJob.organization_id == current_user.organization_id,
        )
        .first()
    )
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


@app.get("/api/v1/vehicles/lookup")
async def v1_vehicle_lookup(
    plate: Optional[str] = Query(default=None),
    vin: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not plate and not vin:
        raise HTTPException(status_code=400, detail="Provide plate or vin")
    normalized_plate = plate.upper() if plate else None

    query = db.query(Vehicle).filter(
        Vehicle.organization_id == current_user.organization_id
    )
    if normalized_plate:
        query = query.filter(Vehicle.number_plate == normalized_plate)
    if vin:
        query = query.filter(Vehicle.vin.ilike(vin))
    record = query.first()
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


@app.post("/api/v1/vehicles", status_code=201)
async def v1_create_vehicle(
    payload: V1VehicleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    db.commit()
    return {"id": vehicle_id, "status": "created"}


@app.get("/api/v1/vehicles/{vehicle_id}/history")
async def v1_vehicle_history(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    inspections = (
        db.query(Inspection)
        .filter(
            Inspection.organization_id == current_user.organization_id,
            (Inspection.plate == vehicle.number_plate)
            | (Inspection.vin == vehicle.vin),
        )
        .order_by(Inspection.date.desc())
        .all()
    )
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


@app.get("/api/v1/garages/nearby")
async def v1_garages_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    sort: str = Query(default="smart_score"),
    damage_type: str = Query(default="dent"),
    ev_only: bool = Query(default=False),
    insurance_only: bool = Query(default=False),
    open_now: bool = Query(default=False),
    max_distance_km: float = Query(default=20.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    garages = db.query(Garage).all()
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


@app.get("/api/v1/garages/insurance-centers")
async def v1_insurance_centers(
    lat: float = Query(...),
    lng: float = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    centers = db.query(InsuranceCenter).all()
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


@app.get("/api/v1/garages/{garage_id}/pricing")
async def v1_garage_pricing(
    garage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    garage = db.query(Garage).filter(Garage.id == garage_id).first()
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
