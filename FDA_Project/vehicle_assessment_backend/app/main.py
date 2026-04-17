import json
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import cv2
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
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
from app.database import Base, engine, get_db
from app.db_models import Claim, Inspection, Organization, OtpCode, RefreshToken, Setting, User
from app.otp_provider import get_otp_provider
from app.pdf_reports import render_inspection_report
from app.services.detector import DamageDetector
from app.utils.assessment import calculate_dsi

detector = DamageDetector()
otp_provider = get_otp_provider()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SeverityLevel = Literal["low", "medium", "high"]
InspectionStatus = Literal["Completed", "Pending", "Failed"]
Theme = Literal["dark", "light"]
UserRole = Literal["admin", "manager", "inspector"]


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


def finding_from_detection(index: int, det: dict, severity: SeverityLevel, triage_category: str) -> DamageFinding:
    return DamageFinding(
        id=f"DMG-{index + 1}",
        type=normalize_detection_type(str(det.get("class", "paint damage"))),
        severity=severity,
        confidence=float(det.get("confidence", 0)),
        category="Cosmetic" if triage_category == "COSMETIC" else "Functional",
        estimate_min=8000 if severity == "high" else 3000 if severity == "medium" else 1200,
        estimate_max=18000 if severity == "high" else 7000 if severity == "medium" else 2800,
        explainability=f"Detected {det.get('class', 'damage')} based on contour/texture anomalies.",
        box=[float(x) for x in det.get("box", [0, 0, 0, 0])],
    )


def issue_token_bundle(db: Session, user: User, organization: Organization) -> AuthResponse:
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
    db = next(get_db())
    try:
        if db.query(Organization).count() > 0:
            return

        org = Organization(id="org_001", name="Acme Claims Pvt Ltd", region="Mumbai", active_inspectors=42)
        admin = User(
            id="usr_001",
            email="ops@insurer.com",
            name="Field Inspector",
            role="admin",
            password_hash=hash_password("password123"),
            organization_id=org.id,
        )
        setting = Setting(organization_id=org.id, push=True, email=True, critical_only=False, theme="dark")

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

        db.add(org)
        db.add(admin)
        db.add(setting)
        for item in sample_inspections:
            db.add(item)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_seed_data()
    yield


app = FastAPI(title="AI Vehicle Assessment Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "AI Vehicle Assessment API is running", "docs": "/docs"}


@app.post("/auth/login", response_model=AuthResponse)
async def auth_login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")

    return issue_token_bundle(db, user, organization)


@app.post("/auth/refresh", response_model=AuthResponse)
async def auth_refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)):
    user = exchange_refresh_token(db, payload.refresh_token)
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")
    return issue_token_bundle(db, user, organization)


@app.post("/auth/logout")
async def auth_logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    token_hash = hash_secret(payload.refresh_token)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token_record:
        token_record.revoked = True
        db.commit()
    return {"message": "Logged out"}


@app.post("/auth/forgot-password")
async def auth_forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        return {"message": "If this email exists, an OTP has been sent", "otp_required": True, "channel": "email"}

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

    otp_provider.send_otp(user.email, otp_code)
    return {"message": f"OTP sent to {user.email}", "otp_required": True, "channel": "email"}


@app.post("/auth/verify-otp", response_model=AuthResponse)
async def auth_verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    otp_record = (
        db.query(OtpCode)
        .filter(OtpCode.email == user.email, OtpCode.purpose == "forgot_password", OtpCode.used.is_(False))
        .order_by(OtpCode.id.desc())
        .first()
    )
    if not otp_record or ensure_utc(otp_record.expires_at) < utc_now() or otp_record.code_hash != hash_secret(payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    otp_record.used = True
    db.commit()

    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")

    return issue_token_bundle(db, user, organization)


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

    avg_health = int(sum([item.health_score for item in all_items]) / len(all_items)) if all_items else 100
    health = FleetHealth(
        score=avg_health,
        attention_vehicles=len(attention),
        inspections_today=len([item for item in all_items if item.date.date() == utc_now().date()]),
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
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as output_file:
        output_file.write(await file.read())

    raw_detections, processed_img_path = detector.analyze_vehicle(str(file_path))

    image = cv2.imread(str(file_path))
    dsi_score = calculate_dsi(raw_detections, image.shape) if image is not None else 0
    triage_category = "COSMETIC" if dsi_score < 40 else "STRUCTURAL/FUNCTIONAL"
    severity = map_severity(dsi_score)

    finding_models = [
        finding_from_detection(index=index, det=det, severity=severity, triage_category=triage_category)
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
async def get_result_image(filename: str, current_user: User = Depends(get_current_user)):
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
    query = db.query(Inspection).filter(Inspection.organization_id == current_user.organization_id)

    if search:
        search_value = f"%{search.lower()}%"
        query = query.filter((Inspection.plate.ilike(search_value)) | (Inspection.model.ilike(search_value)))

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
        .filter(Inspection.id == inspection_id, Inspection.organization_id == current_user.organization_id)
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
        .filter(Inspection.id == inspection_id, Inspection.organization_id == current_user.organization_id)
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
            "X-Report-Signature": hash_secret(inspection_id + str(record.date.timestamp())),
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
        .filter(Inspection.id == payload.inspection_id, Inspection.organization_id == current_user.organization_id)
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
    inspections = db.query(Inspection).filter(Inspection.organization_id == current_user.organization_id).all()
    counts = {"scratch": 0, "dent": 0, "crack": 0, "broken part": 0, "paint damage": 0}

    for inspection in inspections:
        for item in json.loads(inspection.findings_json or "[]"):
            kind = item.get("type", "paint damage")
            if kind not in counts:
                kind = "paint damage"
            counts[kind] += 1

    return {"items": [{"category": key, "count": value} for key, value in counts.items()]}


@app.get("/analytics/severity-trends")
async def analytics_severity_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspections = db.query(Inspection).filter(Inspection.organization_id == current_user.organization_id).all()
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
    inspections = db.query(Inspection).filter(Inspection.organization_id == current_user.organization_id).all()
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
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    setting = db.query(Setting).filter(Setting.organization_id == current_user.organization_id).first()
    if not org or not setting:
        raise HTTPException(status_code=404, detail="Settings not found")

    return SettingsResponse(
        organization=OrganizationInfo(id=org.id, name=org.name, region=org.region, active_inspectors=org.active_inspectors),
        notifications=NotificationPreferences(push=setting.push, email=setting.email, critical_only=setting.critical_only),
        theme=setting.theme,
    )


@app.patch("/settings", response_model=SettingsResponse)
async def patch_settings(
    payload: SettingsPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    setting = db.query(Setting).filter(Setting.organization_id == current_user.organization_id).first()
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
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
        organization=OrganizationInfo(id=org.id, name=org.name, region=org.region, active_inspectors=org.active_inspectors),
        notifications=NotificationPreferences(push=setting.push, email=setting.email, critical_only=setting.critical_only),
        theme=setting.theme,
    )
