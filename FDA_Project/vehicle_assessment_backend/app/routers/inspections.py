import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async, hash_secret
from app.database import get_async_db
from app.db_models import Inspection, User
from app.pdf_reports import render_inspection_report
from app.services.detector import DamageDetector
from app.utils.assessment import calculate_dsi

router = APIRouter(tags=["inspections"])

detector = DamageDetector()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SeverityLevel = Literal["low", "medium", "high"]
InspectionStatus = Literal["Completed", "Pending", "Failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _validate_upload(file: UploadFile, payload: bytes) -> None:
    max_size_bytes = 8 * 1024 * 1024
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


def _write_bytes(path: Path, payload: bytes) -> None:
    with open(path, "wb") as output_file:
        output_file.write(payload)


def _resolve_result_file(filename: str) -> Path | None:
    if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
        return None
    return next(
        (
            candidate
            for candidate in UPLOAD_DIR.iterdir()
            if candidate.is_file() and candidate.name == filename
        ),
        None,
    )


@router.post("/assess-damage/")
async def assess_damage(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    payload = await file.read()
    await asyncio.to_thread(_validate_upload, file, payload)

    base_name = Path(file.filename or "upload").name
    sanitized_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    safe_name = f"{uuid.uuid4().hex}_{sanitized_name}"
    file_path = UPLOAD_DIR / safe_name
    await asyncio.to_thread(_write_bytes, file_path, payload)

    raw_detections, processed_img_path = await asyncio.to_thread(
        detector.analyze_vehicle, str(file_path)
    )
    image = await asyncio.to_thread(cv2.imread, str(file_path))
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
    await db.commit()

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


@router.get("/view-result/{filename}")
async def get_result_image(
    filename: str, current_user: User = Depends(get_current_user_async)
):
    _ = current_user
    file_path = await asyncio.to_thread(_resolve_result_file, filename)
    if file_path:
        return FileResponse(file_path.resolve())
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/inspections", response_model=list[InspectionHistoryItem])
async def list_inspections(
    search: Optional[str] = Query(default=None),
    severity: Optional[SeverityLevel] = Query(default=None),
    status: Optional[InspectionStatus] = Query(default=None),
    date: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(
        select(Inspection).where(
            Inspection.organization_id == current_user.organization_id
        )
    )
    records = result.scalars().all()

    if search:
        search_value = search.lower()
        records = [
            item
            for item in records
            if search_value in (item.plate or "").lower()
            or search_value in (item.model or "").lower()
        ]
    if severity:
        records = [item for item in records if item.severity == severity]
    if status:
        records = [item for item in records if item.status == status]
    records = sorted(records, key=lambda item: item.date, reverse=True)
    if date:
        records = [item for item in records if item.date.date().isoformat() == date]

    return [to_history_item(item) for item in records]


@router.get("/inspections/{inspection_id}", response_model=InspectionDetail)
async def get_inspection_detail(
    inspection_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(
        select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return to_inspection_detail(record)


@router.get("/inspections/{inspection_id}/report.pdf")
async def download_report(
    inspection_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(
        select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.organization_id == current_user.organization_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found")

    detail = to_inspection_detail(record)
    blockchain_payload = {
        "inspection_id": detail.inspection_id,
        "plate": detail.vehicle.plate,
        "model": detail.vehicle.model,
        "inspected_at": detail.vehicle.inspected_at,
        "health_score": detail.health_score,
        "triage_category": detail.triage_category,
        "findings": [item.model_dump() for item in detail.findings],
    }
    blockchain_hash = hashlib.sha256(
        json.dumps(blockchain_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    pdf_bytes = render_inspection_report(
        {
            "inspection_id": detail.inspection_id,
            "vehicle": detail.vehicle.model_dump(),
            "health_score": detail.health_score,
            "triage_category": detail.triage_category,
            "findings": [item.model_dump() for item in detail.findings],
            "blockchain_hash": blockchain_hash,
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
            "X-Blockchain-Hash": blockchain_hash,
        },
    )
