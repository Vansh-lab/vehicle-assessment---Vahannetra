from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class WebhookDeliveryAttempt:
    attempt: int
    scheduled_at: datetime
    reason: str


def build_signature(secret: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def build_retry_schedule(max_attempts: int = 5) -> list[WebhookDeliveryAttempt]:
    attempts: list[WebhookDeliveryAttempt] = []
    now = datetime.now(timezone.utc)
    backoffs = [0, 5, 15, 60, 180]
    for attempt in range(1, max_attempts + 1):
        delay_minutes = backoffs[min(attempt - 1, len(backoffs) - 1)]
        attempts.append(
            WebhookDeliveryAttempt(
                attempt=attempt,
                scheduled_at=now + timedelta(minutes=delay_minutes),
                reason="scheduled",
            )
        )
    return attempts
