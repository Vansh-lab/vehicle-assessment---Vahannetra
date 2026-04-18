from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.settings import settings


class IntegrationError(Exception):
    pass


class IntegrationTimeoutError(IntegrationError):
    pass


class IntegrationUnavailableError(IntegrationError):
    pass


class CircuitOpenError(IntegrationError):
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int
    recovery_seconds: int
    failure_count: int = 0
    opened_at: datetime | None = None

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def can_attempt(self) -> bool:
        if self.opened_at is None:
            return True
        if self._now() >= self.opened_at + timedelta(seconds=self.recovery_seconds):
            self.opened_at = None
            self.failure_count = 0
            return True
        return False

    def on_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def on_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = self._now()


@dataclass(frozen=True)
class InsurerClaimResult:
    provider_reference: str
    accepted: bool
    status: str


@dataclass(frozen=True)
class VahanVehicleRecord:
    number_plate: str
    policy_valid: bool
    source: str


_breaker_vahan = CircuitBreaker(
    name="vahan",
    failure_threshold=settings.integration_circuit_failures,
    recovery_seconds=settings.integration_circuit_recovery_seconds,
)
_breaker_insurer = CircuitBreaker(
    name="insurer",
    failure_threshold=settings.integration_circuit_failures,
    recovery_seconds=settings.integration_circuit_recovery_seconds,
)


async def _request_json(
    *,
    method: str,
    url: str,
    timeout_seconds: float,
    max_retries: int,
    circuit: CircuitBreaker,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not circuit.can_attempt():
        raise CircuitOpenError(f"{circuit.name} connector circuit is open")

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            timeout = httpx.Timeout(timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, json=json_payload)
                response.raise_for_status()
                circuit.on_success()
                body = response.json()
                return body if isinstance(body, dict) else {"data": body}
        except httpx.TimeoutException as exc:
            circuit.on_failure()
            last_error = IntegrationTimeoutError(f"{circuit.name} timeout: {exc}")
        except (httpx.HTTPError, ValueError) as exc:
            circuit.on_failure()
            last_error = IntegrationUnavailableError(
                f"{circuit.name} unavailable: {exc}"
            )

        if attempt < max_retries:
            await asyncio.sleep(min(0.2 * (2**attempt), 1.0))

    raise last_error or IntegrationUnavailableError(f"{circuit.name} request failed")


class VahanConnector:
    async def lookup_vehicle(self, number_plate: str) -> VahanVehicleRecord:
        if settings.integration_mode.lower() != "live":
            return VahanVehicleRecord(
                number_plate=number_plate.upper(),
                policy_valid=True,
                source="mock",
            )

        payload = await _request_json(
            method="POST",
            url=f"{settings.vahan_base_url.rstrip('/')}/vehicles/lookup",
            timeout_seconds=settings.integration_timeout_seconds,
            max_retries=settings.integration_max_retries,
            circuit=_breaker_vahan,
            json_payload={"number_plate": number_plate},
        )
        return VahanVehicleRecord(
            number_plate=str(payload.get("number_plate", number_plate)).upper(),
            policy_valid=bool(payload.get("policy_valid", False)),
            source="live",
        )


class InsurerConnector:
    async def submit_claim(
        self,
        *,
        inspection_id: str,
        destination: str,
        organization_id: str,
    ) -> InsurerClaimResult:
        normalized_destination = destination.upper().replace(" ", "-")
        if settings.integration_mode.lower() != "live":
            hash_input = f"{inspection_id}:{organization_id}:{normalized_destination}"
            suffix = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:8].upper()
            return InsurerClaimResult(
                provider_reference=f"{normalized_destination}-{suffix}",
                accepted=True,
                status="Submitted",
            )

        payload = await _request_json(
            method="POST",
            url=f"{settings.insurer_base_url.rstrip('/')}/claims",
            timeout_seconds=settings.integration_timeout_seconds,
            max_retries=settings.integration_max_retries,
            circuit=_breaker_insurer,
            json_payload={
                "inspection_id": inspection_id,
                "destination": destination,
                "organization_id": organization_id,
            },
        )
        provider_reference = str(payload.get("provider_reference", "")).strip()
        if not provider_reference:
            provider_reference = f"{normalized_destination}-{hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:8].upper()}"
        return InsurerClaimResult(
            provider_reference=provider_reference,
            accepted=bool(payload.get("accepted", True)),
            status=str(payload.get("status", "Submitted")),
        )


_vahan_connector = VahanConnector()
_insurer_connector = InsurerConnector()


def get_vahan_connector() -> VahanConnector:
    return _vahan_connector


def get_insurer_connector() -> InsurerConnector:
    return _insurer_connector
