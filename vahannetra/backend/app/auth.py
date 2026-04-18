from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vahannetra.backend.app.core.settings import settings

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    role: str
    organization_id: str


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization",
        )

    configured_token = settings.jwt_secret
    if credentials.credentials != configured_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return AuthPrincipal(
        subject="phase2-user",
        role="admin",
        organization_id="org_001",
    )
