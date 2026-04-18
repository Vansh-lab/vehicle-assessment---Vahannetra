import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.database import Base, SessionLocal, apply_rls_policies, engine
from app.db_models import (
    Garage,
    InsuranceCenter,
    Inspection,
    Organization,
    Setting,
    User,
    Vehicle,
)

MAX_PLATE_LENGTH = 12
MIN_VIN_LENGTH = 17


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def init_seed_data() -> None:
    Base.metadata.create_all(bind=engine)
    apply_rls_policies()
    db = SessionLocal()
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
                            {
                                "id": "DMG-1",
                                "type": "dent",
                                "severity": "high",
                                "confidence": 0.93,
                                "category": "Functional",
                                "estimate_min": 8500,
                                "estimate_max": 14000,
                                "explainability": "Panel deformation and contour discontinuity suggest high impact dent.",
                                "box": [40, 80, 210, 220],
                            },
                            {
                                "id": "DMG-2",
                                "type": "scratch",
                                "severity": "medium",
                                "confidence": 0.88,
                                "category": "Cosmetic",
                                "estimate_min": 2500,
                                "estimate_max": 4900,
                                "explainability": "Linear surface discontinuity indicates layered paint damage.",
                                "box": [250, 120, 390, 195],
                            },
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
