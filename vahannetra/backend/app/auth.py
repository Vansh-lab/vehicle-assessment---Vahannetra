from __future__ import annotations

from dataclasses import dataclass

import jwt
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

    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth secret is not configured",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "org_id", "exp", "iat"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    return AuthPrincipal(
        subject=str(payload["sub"]),
        role=str(payload["role"]),
        organization_id=str(payload["org_id"]),
    )
