import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import cv2
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, EmailStr

from app.services.detector import DamageDetector
from app.utils.assessment import calculate_dsi

app = FastAPI(title="AI Vehicle Assessment Backend")
detector = DamageDetector()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SeverityLevel = Literal["low", "medium", "high"]
InspectionStatus = Literal["Completed", "Pending", "Failed"]
Theme = Literal["dark", "light"]


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


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


MOCK_HISTORY: list[InspectionHistoryItem] = [
    InspectionHistoryItem(
        id="INSP-1021",
        plate="MH12AB9087",
        model="Hyundai i20",
        date="2026-04-15T10:20:00Z",
        severity="medium",
        status="Completed",
        risk_score=58,
    ),
    InspectionHistoryItem(
        id="INSP-1022",
        plate="DL3CB7781",
        model="Honda Activa",
        date="2026-04-15T11:42:00Z",
        severity="low",
        status="Completed",
        risk_score=31,
    ),
    InspectionHistoryItem(
        id="INSP-1023",
        plate="KA05MN2211",
        model="Tata Nexon",
        date="2026-04-15T13:15:00Z",
        severity="high",
        status="Completed",
        risk_score=84,
    ),
]

MOCK_DETAILS: dict[str, InspectionDetail] = {
    "INSP-1021": InspectionDetail(
        inspection_id="INSP-1021",
        vehicle=VehicleSummary(
            plate="MH12AB9087",
            model="Hyundai i20",
            vin="MA3EHKD17A1234567",
            type="4W",
            inspected_at="2026-04-15T10:20:00Z",
        ),
        health_score=63,
        triage_category="STRUCTURAL/FUNCTIONAL",
        processed_image_url="uploads/Sample2_Image_detected.jpg",
        findings=[
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
            ),
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
            ),
        ],
    )
}

SETTINGS_STATE = SettingsResponse(
    organization=OrganizationInfo(name="Acme Claims Pvt Ltd", region="Mumbai", active_inspectors=42),
    notifications=NotificationPreferences(push=True, email=True, critical_only=False),
    theme="dark",
)


def issue_token_bundle(email: str):
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "access_token": secrets.token_urlsafe(24),
        "refresh_token": secrets.token_urlsafe(32),
        "token_type": "bearer",
        "expires_in": 3600,
        "issued_at": now,
        "user": {
            "id": "usr_001",
            "name": "Field Inspector",
            "email": email,
            "role": "inspector",
        },
        "organization": {
            "id": "org_001",
            "name": SETTINGS_STATE.organization.name,
            "region": SETTINGS_STATE.organization.region,
        },
    }


def map_severity(score: float) -> SeverityLevel:
    if score > 70:
        return "high"
    if score > 35:
        return "medium"
    return "low"


@app.get("/")
async def root():
    return {"message": "AI Vehicle Assessment API is running", "docs": "/docs"}


@app.post("/auth/login")
async def auth_login(payload: AuthLoginRequest):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    return issue_token_bundle(payload.email)


@app.post("/auth/forgot-password")
async def auth_forgot_password(payload: ForgotPasswordRequest):
    return {
        "message": f"Password reset OTP sent to {payload.email}",
        "otp_required": True,
        "channel": "email",
    }


@app.post("/auth/verify-otp")
async def auth_verify_otp(payload: VerifyOtpRequest):
    if payload.otp != "123456":
        raise HTTPException(status_code=400, detail="Invalid OTP")
    return issue_token_bundle(payload.email)


@app.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview():
    health = FleetHealth(score=82, attention_vehicles=14, inspections_today=28, active_alerts=5)
    attention = [item for item in MOCK_HISTORY if item.severity in ("medium", "high")]
    return DashboardOverviewResponse(
        fleet_health=health,
        recent_inspections=MOCK_HISTORY,
        vehicles_requiring_attention=attention,
    )


@app.post("/assess-damage/")
async def assess_damage(file: UploadFile = File(...)):
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as output_file:
        output_file.write(await file.read())

    raw_detections, processed_img_path = detector.analyze_vehicle(str(file_path))

    image = cv2.imread(str(file_path))
    dsi_score = calculate_dsi(raw_detections, image.shape) if image is not None else 0
    triage_category = "COSMETIC" if dsi_score < 40 else "STRUCTURAL/FUNCTIONAL"

    return {
        "inspection_summary": {
            "dsi_score": dsi_score,
            "overall_severity": "High" if dsi_score > 60 else "Moderate",
            "triage_category": triage_category,
        },
        "processed_image_url": f"uploads/{Path(processed_img_path).name}",
        "findings": raw_detections,
    }


@app.get("/view-result/{filename}")
async def get_result_image(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/inspections", response_model=list[InspectionHistoryItem])
async def list_inspections(
    search: Optional[str] = Query(default=None),
    severity: Optional[SeverityLevel] = Query(default=None),
    status: Optional[InspectionStatus] = Query(default=None),
    date: Optional[str] = Query(default=None),
):
    items = MOCK_HISTORY[:]

    if search:
        query = search.lower()
        items = [item for item in items if query in item.plate.lower() or query in item.model.lower()]

    if severity:
        items = [item for item in items if item.severity == severity]

    if status:
        items = [item for item in items if item.status == status]

    if date:
        items = [item for item in items if item.date.startswith(date)]

    return items


@app.get("/inspections/{inspection_id}", response_model=InspectionDetail)
async def get_inspection_detail(inspection_id: str):
    detail = MOCK_DETAILS.get(inspection_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return detail


def build_simple_pdf(content: str) -> bytes:
    text = content.replace("(", "[").replace(")", "]")
    body = f"BT /F1 12 Tf 40 760 Td ({text}) Tj ET"
    pdf = f"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n4 0 obj<< /Length {len(body)} >>stream\n{body}\nendstream\nendobj\n5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\ntrailer<< /Root 1 0 R >>\n%%EOF"
    return pdf.encode("utf-8")


@app.get("/inspections/{inspection_id}/report.pdf")
async def download_report(inspection_id: str):
    detail = MOCK_DETAILS.get(inspection_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Inspection not found")

    summary = (
        f"Inspection: {detail.inspection_id} | Vehicle: {detail.vehicle.plate} {detail.vehicle.model} | "
        f"Health Score: {detail.health_score} | Findings: {len(detail.findings)}"
    )
    payload = build_simple_pdf(summary)
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{inspection_id}.pdf"'},
    )


@app.get("/analytics/damage-distribution")
async def analytics_damage_distribution():
    distribution = {
        "scratch": 12,
        "dent": 8,
        "crack": 3,
        "broken part": 2,
        "paint damage": 7,
    }
    return {"items": [{"category": key, "count": value} for key, value in distribution.items()]}


@app.get("/analytics/severity-trends")
async def analytics_severity_trends():
    return {
        "trends": [
            {"month": "Jan", "low": 28, "medium": 14, "high": 5},
            {"month": "Feb", "low": 22, "medium": 16, "high": 6},
            {"month": "Mar", "low": 30, "medium": 18, "high": 8},
            {"month": "Apr", "low": 26, "medium": 19, "high": 7},
            {"month": "May", "low": 33, "medium": 15, "high": 9},
        ]
    }


@app.get("/analytics/vehicle-risk-ranking")
async def analytics_vehicle_risk_ranking():
    return {
        "ranking": [
            {"model": "Mahindra Bolero", "risk": 82},
            {"model": "Tata Ace", "risk": 78},
            {"model": "Hyundai i20", "risk": 61},
            {"model": "Maruti Swift", "risk": 47},
        ]
    }


@app.get("/settings", response_model=SettingsResponse)
async def get_settings():
    return SETTINGS_STATE


@app.patch("/settings", response_model=SettingsResponse)
async def patch_settings(payload: SettingsPatchRequest):
    global SETTINGS_STATE

    updated_theme = payload.theme or SETTINGS_STATE.theme
    updated_notifications = payload.notifications or SETTINGS_STATE.notifications

    SETTINGS_STATE = SettingsResponse(
        organization=SETTINGS_STATE.organization,
        notifications=updated_notifications,
        theme=updated_theme,
    )
    return SETTINGS_STATE
