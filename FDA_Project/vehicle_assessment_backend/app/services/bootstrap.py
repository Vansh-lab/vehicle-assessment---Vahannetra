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
MARKET = {"scratch": 3500, "dent": 8000, "paint": 6000, "major": 25000}


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


def _price_band(workshop_type: str, seed: int) -> dict[str, int]:
    random.seed(seed)
    if workshop_type == "local":
        factor = random.uniform(0.70, 0.80)
    elif workshop_type == "multi-brand":
        factor = random.uniform(0.90, 0.95)
    else:
        factor = random.uniform(1.10, 1.20)

    def span(base: int, spread: float) -> tuple[int, int]:
        low = int(base * factor)
        high = int(low * spread)
        return low, high

    scratch_min, scratch_max = span(MARKET["scratch"], 1.6)
    dent_min, dent_max = span(MARKET["dent"], 1.55)
    paint_min, paint_max = span(MARKET["paint"], 1.5)
    major_min, major_max = span(MARKET["major"], 1.45)
    labour = int(350 if workshop_type == "local" else 450 if workshop_type == "multi-brand" else 700)
    return {
        "pricing_scratch_min": scratch_min,
        "pricing_scratch_max": scratch_max,
        "pricing_dent_min": dent_min,
        "pricing_dent_max": dent_max,
        "pricing_paint_min": paint_min,
        "pricing_paint_max": paint_max,
        "pricing_major_min": major_min,
        "pricing_major_max": major_max,
        "hourly_labour_rate": labour,
    }


def _garage_seed_rows() -> list[dict]:
    rows = [
        # Delhi (5)
        {"id": "GAR-DEL-001", "name": "Sharma Auto Works", "address": "Shop 12, Karol Bagh, New Delhi", "city": "Delhi", "state": "Delhi", "pincode": "110005", "phone": "+91 9810123456", "latitude": 28.6512, "longitude": 77.1909, "rating": 4.6, "type": "multi-brand", "certs": ["GoMechanic Partner", "MSME Certified"], "years": 12},
        {"id": "GAR-DEL-002", "name": "AutoShield Authorized", "address": "Sector 14, Dwarka, New Delhi", "city": "Delhi", "state": "Delhi", "pincode": "110078", "phone": "+91 9810123457", "latitude": 28.5921, "longitude": 77.0460, "rating": 4.7, "type": "authorized", "certs": ["ISO 9001"], "years": 16},
        {"id": "GAR-DEL-003", "name": "City Dent Masters", "address": "Lajpat Nagar-II, New Delhi", "city": "Delhi", "state": "Delhi", "pincode": "110024", "phone": "+91 9810123458", "latitude": 28.5677, "longitude": 77.2432, "rating": 4.4, "type": "local", "certs": ["MSME"], "years": 9},
        {"id": "GAR-DEL-004", "name": "North Star Motors", "address": "Rohini Sector 7, Delhi", "city": "Delhi", "state": "Delhi", "pincode": "110085", "phone": "+91 9810123459", "latitude": 28.7383, "longitude": 77.1134, "rating": 4.3, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 8},
        {"id": "GAR-DEL-005", "name": "Metro Car Body Shop", "address": "Mayur Vihar Phase 1, Delhi", "city": "Delhi", "state": "Delhi", "pincode": "110091", "phone": "+91 9810123460", "latitude": 28.6077, "longitude": 77.2910, "rating": 4.2, "type": "local", "certs": ["MSME"], "years": 7},
        # Mumbai (5)
        {"id": "GAR-MUM-001", "name": "Prime Auto Works", "address": "Andheri East, Mumbai", "city": "Mumbai", "state": "Maharashtra", "pincode": "400069", "phone": "+91 9876500001", "latitude": 19.1136, "longitude": 72.8697, "rating": 4.6, "type": "authorized", "certs": ["ISO 9001", "MSME"], "years": 12},
        {"id": "GAR-MUM-002", "name": "Budget Car Care", "address": "Powai, Mumbai", "city": "Mumbai", "state": "Maharashtra", "pincode": "400076", "phone": "+91 9876500002", "latitude": 19.1183, "longitude": 72.9052, "rating": 4.3, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 8},
        {"id": "GAR-MUM-003", "name": "Harbor Auto Clinic", "address": "Wadala, Mumbai", "city": "Mumbai", "state": "Maharashtra", "pincode": "400031", "phone": "+91 9876500003", "latitude": 19.0176, "longitude": 72.8562, "rating": 4.2, "type": "local", "certs": ["MSME"], "years": 6},
        {"id": "GAR-MUM-004", "name": "Bandra Panel House", "address": "Bandra West, Mumbai", "city": "Mumbai", "state": "Maharashtra", "pincode": "400050", "phone": "+91 9876500004", "latitude": 19.0596, "longitude": 72.8295, "rating": 4.5, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 10},
        {"id": "GAR-MUM-005", "name": "Southbay Motors", "address": "Colaba, Mumbai", "city": "Mumbai", "state": "Maharashtra", "pincode": "400005", "phone": "+91 9876500005", "latitude": 18.9067, "longitude": 72.8147, "rating": 4.7, "type": "authorized", "certs": ["ISO 9001"], "years": 15},
        # Bengaluru (4)
        {"id": "GAR-BLR-001", "name": "Silicon Auto Lab", "address": "HSR Layout, Bengaluru", "city": "Bengaluru", "state": "Karnataka", "pincode": "560102", "phone": "+91 9845010001", "latitude": 12.9116, "longitude": 77.6474, "rating": 4.5, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 9},
        {"id": "GAR-BLR-002", "name": "Outer Ring Road Motors", "address": "Bellandur, Bengaluru", "city": "Bengaluru", "state": "Karnataka", "pincode": "560103", "phone": "+91 9845010002", "latitude": 12.9279, "longitude": 77.6791, "rating": 4.4, "type": "local", "certs": ["MSME"], "years": 8},
        {"id": "GAR-BLR-003", "name": "Indiranagar Auto Pro", "address": "Indiranagar 100ft Road, Bengaluru", "city": "Bengaluru", "state": "Karnataka", "pincode": "560038", "phone": "+91 9845010003", "latitude": 12.9719, "longitude": 77.6412, "rating": 4.6, "type": "authorized", "certs": ["ISO 9001"], "years": 14},
        {"id": "GAR-BLR-004", "name": "KR Puram Car Hub", "address": "KR Puram, Bengaluru", "city": "Bengaluru", "state": "Karnataka", "pincode": "560036", "phone": "+91 9845010004", "latitude": 13.0008, "longitude": 77.6956, "rating": 4.1, "type": "local", "certs": ["MSME"], "years": 5},
        # Kanpur (5 required names)
        {"id": "GAR-KNP-001", "name": "Kanpur Car Care Centre", "address": "HIG 42-43, Barra 2, Kanpur", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208027", "phone": "+91 9555011001", "latitude": 26.4277, "longitude": 80.3319, "rating": 4.0, "type": "local", "certs": ["MSME"], "years": 11},
        {"id": "GAR-KNP-002", "name": "Super Car Automobile", "address": "D Block 39, Barra Bypass, Kanpur", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208027", "phone": "+91 9555011002", "latitude": 26.4184, "longitude": 80.3255, "rating": 5.0, "type": "local", "certs": ["MSME"], "years": 10},
        {"id": "GAR-KNP-003", "name": "SK Car Workshop", "address": "Plot D-37, Barra 6, Kanpur", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208027", "phone": "+91 9555011003", "latitude": 26.4138, "longitude": 80.3187, "rating": 4.9, "type": "local", "certs": ["MSME"], "years": 9},
        {"id": "GAR-KNP-004", "name": "GoMechanic — Shiv Motors", "address": "E-86 MIG Barra, Kanpur", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208027", "phone": "+91 9555011004", "latitude": 26.4210, "longitude": 80.3348, "rating": 4.2, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 7},
        {"id": "GAR-KNP-005", "name": "Om Auto Centre", "address": "30 Karrhi Road, Maya Market, Kanpur", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208027", "phone": "+91 9555011005", "latitude": 26.4342, "longitude": 80.3401, "rating": 5.0, "type": "local", "certs": ["MSME"], "years": 12},
        # Hyderabad (3)
        {"id": "GAR-HYD-001", "name": "Charminar Auto Tech", "address": "Banjara Hills Road 12, Hyderabad", "city": "Hyderabad", "state": "Telangana", "pincode": "500034", "phone": "+91 9849012001", "latitude": 17.4126, "longitude": 78.4482, "rating": 4.4, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 9},
        {"id": "GAR-HYD-002", "name": "HiTec Car Studio", "address": "Madhapur, Hyderabad", "city": "Hyderabad", "state": "Telangana", "pincode": "500081", "phone": "+91 9849012002", "latitude": 17.4448, "longitude": 78.3915, "rating": 4.3, "type": "local", "certs": ["MSME"], "years": 6},
        {"id": "GAR-HYD-003", "name": "Secunderabad Motors", "address": "S.D. Road, Secunderabad", "city": "Hyderabad", "state": "Telangana", "pincode": "500003", "phone": "+91 9849012003", "latitude": 17.4399, "longitude": 78.4983, "rating": 4.5, "type": "authorized", "certs": ["ISO 9001"], "years": 13},
        # Pune (3)
        {"id": "GAR-PUN-001", "name": "Pune Auto Square", "address": "Baner Road, Pune", "city": "Pune", "state": "Maharashtra", "pincode": "411045", "phone": "+91 9850013001", "latitude": 18.5590, "longitude": 73.7868, "rating": 4.3, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 8},
        {"id": "GAR-PUN-002", "name": "Kothrud Car Care", "address": "Kothrud Depot, Pune", "city": "Pune", "state": "Maharashtra", "pincode": "411038", "phone": "+91 9850013002", "latitude": 18.5074, "longitude": 73.8077, "rating": 4.2, "type": "local", "certs": ["MSME"], "years": 7},
        {"id": "GAR-PUN-003", "name": "Hadapsar Service Hub", "address": "Magarpatta, Pune", "city": "Pune", "state": "Maharashtra", "pincode": "411028", "phone": "+91 9850013003", "latitude": 18.5158, "longitude": 73.9272, "rating": 4.6, "type": "authorized", "certs": ["ISO 9001"], "years": 14},
        # Chennai (3)
        {"id": "GAR-CHE-001", "name": "Marina Auto Works", "address": "Anna Salai, Chennai", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600002", "phone": "+91 9884014001", "latitude": 13.0618, "longitude": 80.2742, "rating": 4.4, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 9},
        {"id": "GAR-CHE-002", "name": "Velachery Body Shop", "address": "Velachery Main Road, Chennai", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600042", "phone": "+91 9884014002", "latitude": 12.9753, "longitude": 80.2204, "rating": 4.2, "type": "local", "certs": ["MSME"], "years": 6},
        {"id": "GAR-CHE-003", "name": "OMR Authorized Care", "address": "Sholinganallur, Chennai", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600119", "phone": "+91 9884014003", "latitude": 12.9010, "longitude": 80.2279, "rating": 4.6, "type": "authorized", "certs": ["ISO 9001"], "years": 15},
        # Kolkata (2)
        {"id": "GAR-KOL-001", "name": "Howrah Auto Bay", "address": "Howrah Maidan, Kolkata", "city": "Kolkata", "state": "West Bengal", "pincode": "711101", "phone": "+91 9903015001", "latitude": 22.5892, "longitude": 88.3106, "rating": 4.1, "type": "local", "certs": ["MSME"], "years": 7},
        {"id": "GAR-KOL-002", "name": "Salt Lake Motors", "address": "Sector V, Salt Lake, Kolkata", "city": "Kolkata", "state": "West Bengal", "pincode": "700091", "phone": "+91 9903015002", "latitude": 22.5755, "longitude": 88.4325, "rating": 4.5, "type": "multi-brand", "certs": ["GoMechanic Partner"], "years": 10},
    ]
    return rows


def _insurance_seed_rows() -> list[dict]:
    return [
        {"id": "INS-DEL-001", "name": "Delhi Claims Desk 1", "insurer_name": "ICICI Lombard", "address": "Connaught Place, Delhi", "city": "Delhi", "phone": "+91-1800-100-0001", "toll_free": "1800-100-0001", "latitude": 28.6315, "longitude": 77.2167, "rating": 4.3},
        {"id": "INS-DEL-002", "name": "Delhi Claims Desk 2", "insurer_name": "Bajaj Allianz", "address": "Karol Bagh, Delhi", "city": "Delhi", "phone": "+91-1800-100-0002", "toll_free": "1800-100-0002", "latitude": 28.6519, "longitude": 77.1909, "rating": 4.1},
        {"id": "INS-MUM-001", "name": "Mumbai Claims Hub 1", "insurer_name": "HDFC Ergo", "address": "BKC, Mumbai", "city": "Mumbai", "phone": "+91-1800-100-0011", "toll_free": "1800-100-0011", "latitude": 19.0707, "longitude": 72.8697, "rating": 4.2},
        {"id": "INS-MUM-002", "name": "Mumbai Claims Hub 2", "insurer_name": "TATA AIG", "address": "Andheri, Mumbai", "city": "Mumbai", "phone": "+91-1800-100-0012", "toll_free": "1800-100-0012", "latitude": 19.1136, "longitude": 72.8697, "rating": 4.0},
        {"id": "INS-BLR-001", "name": "Bengaluru Claim Point 1", "insurer_name": "ICICI Lombard", "address": "Indiranagar, Bengaluru", "city": "Bengaluru", "phone": "+91-1800-100-0021", "toll_free": "1800-100-0021", "latitude": 12.9719, "longitude": 77.6412, "rating": 4.3},
        {"id": "INS-BLR-002", "name": "Bengaluru Claim Point 2", "insurer_name": "Bajaj Allianz", "address": "HSR Layout, Bengaluru", "city": "Bengaluru", "phone": "+91-1800-100-0022", "toll_free": "1800-100-0022", "latitude": 12.9116, "longitude": 77.6474, "rating": 4.2},
        {"id": "INS-KNP-001", "name": "Kanpur Insurance Center 1", "insurer_name": "New India Assurance", "address": "Civil Lines, Kanpur", "city": "Kanpur", "phone": "+91-1800-100-0031", "toll_free": "1800-100-0031", "latitude": 26.4499, "longitude": 80.3319, "rating": 4.1},
        {"id": "INS-KNP-002", "name": "Kanpur Insurance Center 2", "insurer_name": "HDFC Ergo", "address": "Swaroop Nagar, Kanpur", "city": "Kanpur", "phone": "+91-1800-100-0032", "toll_free": "1800-100-0032", "latitude": 26.4798, "longitude": 80.3153, "rating": 4.0},
        {"id": "INS-HYD-001", "name": "Hyderabad Claim Desk 1", "insurer_name": "ICICI Lombard", "address": "Banjara Hills, Hyderabad", "city": "Hyderabad", "phone": "+91-1800-100-0041", "toll_free": "1800-100-0041", "latitude": 17.4126, "longitude": 78.4482, "rating": 4.2},
        {"id": "INS-HYD-002", "name": "Hyderabad Claim Desk 2", "insurer_name": "Bajaj Allianz", "address": "Madhapur, Hyderabad", "city": "Hyderabad", "phone": "+91-1800-100-0042", "toll_free": "1800-100-0042", "latitude": 17.4448, "longitude": 78.3915, "rating": 4.1},
        {"id": "INS-PUN-001", "name": "Pune Claims Help", "insurer_name": "HDFC Ergo", "address": "Baner, Pune", "city": "Pune", "phone": "+91-1800-100-0051", "toll_free": "1800-100-0051", "latitude": 18.5590, "longitude": 73.7868, "rating": 4.2},
        {"id": "INS-PUN-002", "name": "Pune Policy Desk", "insurer_name": "TATA AIG", "address": "Kothrud, Pune", "city": "Pune", "phone": "+91-1800-100-0052", "toll_free": "1800-100-0052", "latitude": 18.5074, "longitude": 73.8077, "rating": 4.0},
        {"id": "INS-CHE-001", "name": "Chennai Claims Point", "insurer_name": "ICICI Lombard", "address": "Anna Salai, Chennai", "city": "Chennai", "phone": "+91-1800-100-0061", "toll_free": "1800-100-0061", "latitude": 13.0618, "longitude": 80.2742, "rating": 4.2},
        {"id": "INS-CHE-002", "name": "Chennai Insurance Hub", "insurer_name": "Bajaj Allianz", "address": "Velachery, Chennai", "city": "Chennai", "phone": "+91-1800-100-0062", "toll_free": "1800-100-0062", "latitude": 12.9753, "longitude": 80.2204, "rating": 4.1},
        {"id": "INS-KOL-001", "name": "Kolkata Claim Support", "insurer_name": "New India Assurance", "address": "Salt Lake, Kolkata", "city": "Kolkata", "phone": "+91-1800-100-0071", "toll_free": "1800-100-0071", "latitude": 22.5755, "longitude": 88.4325, "rating": 4.1},
    ]


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
            db.add(
                User(
                    id="usr_001",
                    email="ops@insurer.com",
                    name="Field Inspector",
                    role="admin",
                    password_hash=hash_password("password123"),
                    organization_id=org.id,
                )
            )

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
            db.add_all(
                [
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
                ]
            )

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
                    rc_valid_until=ensure_utc(datetime.fromisoformat(demo["rc_valid_until"].replace("Z", "+00:00"))),
                    insurance_valid_until=ensure_utc(datetime.fromisoformat(demo["insurance_valid_until"].replace("Z", "+00:00"))),
                    vahan_data=json.dumps(demo),
                    previous_claim_count=demo["previous_claim_count"],
                    blacklist_status=demo["blacklist_status"],
                )
            )

        if db.query(Garage).count() < 30:
            db.query(Garage).delete()
            for idx, row in enumerate(_garage_seed_rows(), start=1):
                price = _price_band(row["type"], seed=idx)
                services = ["Dent repair", "Paint work", "Insurance approved"]
                if row["type"] != "authorized":
                    services.append("EV certified")
                db.add(
                    Garage(
                        id=row["id"],
                        name=row["name"],
                        address=row["address"],
                        city=row["city"],
                        state=row["state"],
                        pincode=row["pincode"],
                        phone=row["phone"],
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        rating=row["rating"],
                        is_open_now=True,
                        services=json.dumps(services),
                        is_insurance_approved=True,
                        is_ev_certified=True,
                        google_maps_url=f"https://maps.google.com/?q={row['name'].replace(' ', '+')}+{row['city']}",
                        workshop_type=row["type"],
                        certifications=json.dumps(row["certs"]),
                        years_in_business=row["years"],
                        **price,
                    )
                )

        if db.query(InsuranceCenter).count() < 15:
            db.query(InsuranceCenter).delete()
            for row in _insurance_seed_rows():
                db.add(
                    InsuranceCenter(
                        id=row["id"],
                        name=row["name"],
                        insurer_name=row["insurer_name"],
                        address=row["address"],
                        city=row["city"],
                        phone=row["phone"],
                        toll_free=row["toll_free"],
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        rating=row["rating"],
                        services=json.dumps(["Claim registration", "Cashless support"]),
                        cashless_network=True,
                        avg_claim_processing_days=6,
                        cashless_garage_count=100,
                    )
                )

        db.commit()
    finally:
        db.close()
