import asyncio
import hmac
import json
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token_async,
    exchange_refresh_token_async,
    hash_secret,
    verify_password,
)
from app.database import get_async_db
from app.db_models import OtpCode, OtpDeliveryEvent, Organization, RefreshToken, User
from app.otp_provider import get_otp_provider
from app.secrets import get_secret

router = APIRouter(prefix="/auth", tags=["auth"])

otp_provider = get_otp_provider()


class AuthLoginRequest(BaseModel):
    email: str
    password: str
    otp: str | None = None


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class LogoutRequest(BaseModel):
    refresh_token: str


class OtpDeliveryCallback(BaseModel):
    provider_message_id: str
    status: str
    error_message: str | None = None
    payload: dict | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    issued_at: str
    user: dict
    organization: dict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def isoformat_utc_z(value: datetime) -> str:
    return ensure_utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def issue_token_bundle_async(
    db: AsyncSession, user: User, organization: Organization
) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=await create_refresh_token_async(db, user),
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


@router.post("/login", response_model=AuthResponse)
async def auth_login(
    payload: AuthLoginRequest, db: AsyncSession = Depends(get_async_db)
):
    user_result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = user_result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")
    return await issue_token_bundle_async(db, user, organization)


@router.post("/refresh", response_model=AuthResponse)
async def auth_refresh(
    payload: AuthRefreshRequest, db: AsyncSession = Depends(get_async_db)
):
    user = await exchange_refresh_token_async(db, payload.refresh_token)
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")
    return await issue_token_bundle_async(db, user, organization)


@router.post("/logout")
async def auth_logout(payload: LogoutRequest, db: AsyncSession = Depends(get_async_db)):
    token_hash = hash_secret(payload.refresh_token)
    token_result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = token_result.scalar_one_or_none()
    if token_record:
        token_record.revoked = True
        await db.commit()
    return {"message": "Logged out"}


@router.post("/forgot-password")
async def auth_forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_async_db)
):
    user_result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = user_result.scalar_one_or_none()
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
    await db.commit()

    delivery_event = OtpDeliveryEvent(
        email=user.email, organization_id=user.organization_id, status="pending"
    )
    db.add(delivery_event)
    await db.commit()
    await db.refresh(delivery_event)

    send_result = await asyncio.to_thread(otp_provider.send_otp, user.email, otp_code)
    delivery_event.provider = send_result.provider
    delivery_event.provider_message_id = send_result.provider_message_id
    delivery_event.status = send_result.status
    delivery_event.attempts = send_result.attempts
    delivery_event.error_message = send_result.error_message
    await db.commit()
    return {
        "message": f"OTP sent to {user.email}",
        "otp_required": True,
        "channel": "email",
    }


@router.post("/verify-otp", response_model=AuthResponse)
async def auth_verify_otp(
    payload: VerifyOtpRequest, db: AsyncSession = Depends(get_async_db)
):
    user_result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    otp_result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.email == user.email,
            OtpCode.purpose == "forgot_password",
            OtpCode.used.is_(False),
        )
        .order_by(OtpCode.id.desc())
    )
    otp_record = otp_result.scalars().first()
    if (
        not otp_record
        or ensure_utc(otp_record.expires_at) < utc_now()
        or otp_record.code_hash != hash_secret(payload.otp)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    otp_record.used = True
    await db.commit()

    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=500, detail="Organization not found")

    return await issue_token_bundle_async(db, user, organization)


@router.post("/otp/delivery-callback")
async def auth_otp_delivery_callback(
    payload: OtpDeliveryCallback,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    callback_secret = get_secret("OTP_CALLBACK_SECRET", "dev-callback-secret")
    provided = request.headers.get("X-Callback-Secret")
    if not provided or not hmac.compare_digest(provided, callback_secret):
        raise HTTPException(status_code=401, detail="Invalid callback secret")

    event_result = await db.execute(
        select(OtpDeliveryEvent)
        .where(OtpDeliveryEvent.provider_message_id == payload.provider_message_id)
        .order_by(OtpDeliveryEvent.id.desc())
    )
    event = event_result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Delivery event not found")

    event.status = payload.status
    event.error_message = payload.error_message or ""
    event.callback_payload = json.dumps(payload.payload or {})
    await db.commit()
    return {"ok": True}
