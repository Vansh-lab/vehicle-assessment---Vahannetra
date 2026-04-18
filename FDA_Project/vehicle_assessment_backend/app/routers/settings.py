from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_async, require_roles_async
from app.database import get_async_db
from app.db_models import Organization, Setting, User

Theme = str

router = APIRouter(tags=["settings"])


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
    theme: Theme | None = None
    notifications: NotificationPreferences | None = None


def to_settings_response(org: Organization, setting: Setting) -> SettingsResponse:
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


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    setting_result = await db.execute(
        select(Setting).where(Setting.organization_id == current_user.organization_id)
    )
    setting = setting_result.scalar_one_or_none()
    if not org or not setting:
        raise HTTPException(status_code=404, detail="Settings not found")
    return to_settings_response(org, setting)


@router.patch("/settings", response_model=SettingsResponse)
async def patch_settings(
    payload: SettingsPatchRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_roles_async("admin", "manager")),
):
    setting_result = await db.execute(
        select(Setting).where(Setting.organization_id == current_user.organization_id)
    )
    setting = setting_result.scalar_one_or_none()
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    if not setting or not org:
        raise HTTPException(status_code=404, detail="Settings not found")

    if payload.theme is not None:
        setting.theme = payload.theme
    if payload.notifications is not None:
        setting.push = payload.notifications.push
        setting.email = payload.notifications.email
        setting.critical_only = payload.notifications.critical_only

    await db.commit()
    await db.refresh(setting)
    return to_settings_response(org, setting)
