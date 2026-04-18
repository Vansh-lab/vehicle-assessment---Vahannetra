from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    active_inspectors: Mapped[int] = mapped_column(Integer, default=0)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="organization"
    )
    setting: Mapped["Setting"] = relationship(
        back_populates="organization", uselist=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="inspector")
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )

    organization: Mapped[Organization] = relationship(back_populates="users")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), default="forgot_password")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class OtpDeliveryEvent(Base):
    __tablename__ = "otp_delivery_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    email: Mapped[str] = mapped_column(String(320), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="console")
    provider_message_id: Mapped[str] = mapped_column(
        String(200), index=True, default=""
    )
    status: Mapped[str] = mapped_column(String(40), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(String(500), default="")
    callback_payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    plate: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), index=True)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), default="4W")
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    severity: Mapped[str] = mapped_column(String(16), default="low")
    status: Mapped[str] = mapped_column(String(20), default="Completed")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    triage_category: Mapped[str] = mapped_column(String(40), default="COSMETIC")
    processed_image_url: Mapped[str] = mapped_column(String(255), default="")
    findings_json: Mapped[str] = mapped_column(Text, default="[]")

    organization: Mapped[Organization] = relationship(back_populates="inspections")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), unique=True, index=True
    )
    push: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[bool] = mapped_column(Boolean, default=True)
    critical_only: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(16), default="dark")

    organization: Mapped[Organization] = relationship(back_populates="setting")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"), index=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="Submitted")
    provider_ref: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ClientErrorEvent(Base):
    __tablename__ = "client_error_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    level: Mapped[str] = mapped_column(String(20), default="error")
    message: Mapped[str] = mapped_column(String(1000), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    stack: Mapped[str] = mapped_column(Text, default="")
    route: Mapped[str] = mapped_column(String(255), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    number_plate: Mapped[str] = mapped_column(String(40), index=True)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), default="4W")
    make: Mapped[str] = mapped_column(String(64), default="Unknown")
    model: Mapped[str] = mapped_column(String(64), default="Unknown")
    year: Mapped[int] = mapped_column(Integer, default=2020)
    fuel_type: Mapped[str] = mapped_column(String(32), default="Petrol")
    is_ev: Mapped[bool] = mapped_column(Boolean, default=False)
    rto: Mapped[str] = mapped_column(String(32), default="Unknown")
    rc_valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    insurance_valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    vahan_data: Mapped[str] = mapped_column(Text, default="{}")
    previous_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    blacklist_status: Mapped[str] = mapped_column(String(64), default="Not Blacklisted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class InspectionJob(Base):
    __tablename__ = "inspection_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehicles.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    use_case: Mapped[str] = mapped_column(String(64), default="insurance_claim")
    input_type: Mapped[str] = mapped_column(String(24), default="photo")
    s3_image_keys: Mapped[str] = mapped_column(Text, default="[]")
    s3_video_key: Mapped[str] = mapped_column(String(255), default="")
    s3_annotated_key: Mapped[str] = mapped_column(String(255), default="")
    s3_pdf_key: Mapped[str] = mapped_column(String(255), default="")
    dsq_score: Mapped[float] = mapped_column(Float, default=0.0)
    dsq_breakdown: Mapped[str] = mapped_column(Text, default="{}")
    overall_severity: Mapped[str] = mapped_column(String(16), default="low")
    confidence_overall: Mapped[float] = mapped_column(Float, default=0.0)
    fraud_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    fraud_flags: Mapped[str] = mapped_column(Text, default="[]")
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=True)
    repair_cost_min_inr: Mapped[int] = mapped_column(Integer, default=0)
    repair_cost_max_inr: Mapped[int] = mapped_column(Integer, default=0)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    insurance_claim_steps: Mapped[str] = mapped_column(Text, default="")
    blockchain_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Garage(Base):
    __tablename__ = "garages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(64), default="")
    state: Mapped[str] = mapped_column(String(64), default="")
    pincode: Mapped[str] = mapped_column(String(16), default="")
    phone: Mapped[str] = mapped_column(String(24), default="")
    latitude: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    longitude: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    is_open_now: Mapped[bool] = mapped_column(Boolean, default=True)
    services: Mapped[str] = mapped_column(Text, default="[]")
    is_insurance_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ev_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    google_maps_url: Mapped[str] = mapped_column(String(500), default="")
    pricing_dent_min: Mapped[int] = mapped_column(Integer, default=0)
    pricing_dent_max: Mapped[int] = mapped_column(Integer, default=0)
    pricing_scratch_min: Mapped[int] = mapped_column(Integer, default=0)
    pricing_scratch_max: Mapped[int] = mapped_column(Integer, default=0)
    pricing_paint_min: Mapped[int] = mapped_column(Integer, default=0)
    pricing_paint_max: Mapped[int] = mapped_column(Integer, default=0)
    pricing_major_min: Mapped[int] = mapped_column(Integer, default=0)
    pricing_major_max: Mapped[int] = mapped_column(Integer, default=0)
    hourly_labour_rate: Mapped[int] = mapped_column(Integer, default=0)
    workshop_type: Mapped[str] = mapped_column(String(32), default="local")
    certifications: Mapped[str] = mapped_column(Text, default="[]")
    years_in_business: Mapped[int] = mapped_column(Integer, default=1)


class InsuranceCenter(Base):
    __tablename__ = "insurance_centers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    insurer_name: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str] = mapped_column(String(24), default="")
    toll_free: Mapped[str] = mapped_column(String(24), default="")
    latitude: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    longitude: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    services: Mapped[str] = mapped_column(Text, default="[]")
    cashless_network: Mapped[bool] = mapped_column(Boolean, default=True)
    avg_claim_processing_days: Mapped[int] = mapped_column(Integer, default=7)
    cashless_garage_count: Mapped[int] = mapped_column(Integer, default=0)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    target_url: Mapped[str] = mapped_column(String(1024))
    event_type: Mapped[str] = mapped_column(String(64), default="inspection.completed")
    secret: Mapped[str] = mapped_column(String(128), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class WebhookDeadLetter(Base):
    __tablename__ = "webhook_dead_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    webhook_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    target_url: Mapped[str] = mapped_column(String(1024), default="")
    event_type: Mapped[str] = mapped_column(String(64), default="inspection.completed")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    signature: Mapped[str] = mapped_column(String(256), default="")
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
