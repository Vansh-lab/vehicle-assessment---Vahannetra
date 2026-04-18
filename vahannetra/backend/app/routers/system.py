from __future__ import annotations

from fastapi import APIRouter, Depends

from vahannetra.backend.app.auth import AuthPrincipal, get_current_principal
from vahannetra.backend.app.schemas import CapabilityResponse, PrincipalResponse

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/capabilities", response_model=CapabilityResponse)
async def capabilities(
    _: AuthPrincipal = Depends(get_current_principal),
) -> CapabilityResponse:
    return CapabilityResponse(
        backend_foundation=True,
        auth=True,
        async_db=True,
        routers=["health", "system", "analyze"],
    )


@router.get("/me", response_model=PrincipalResponse)
async def me(
    principal: AuthPrincipal = Depends(get_current_principal),
) -> PrincipalResponse:
    return PrincipalResponse(
        subject=principal.subject,
        role=principal.role,
        organization_id=principal.organization_id,
    )
