from __future__ import annotations

import hashlib
import json
import logging

import requests

from app.database import SessionLocal
from app.db_models import WebhookDeadLetter
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _build_idempotency_key(target_url: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{target_url}|{body}".encode("utf-8")).hexdigest()


@celery_app.task(bind=True, max_retries=5)
def deliver_webhook(
    self,
    target_url: str,
    payload: dict,
    signature: str,
    organization_id: str = "",
    webhook_id: str = "",
    event_type: str = "inspection.completed",
) -> dict:
    idempotency_key = _build_idempotency_key(target_url, payload)
    try:
        response = requests.post(
            target_url,
            json=payload,
            timeout=8,
            headers={
                "Content-Type": "application/json",
                "X-VahanNetra-Signature": signature,
                "Idempotency-Key": idempotency_key,
                "User-Agent": "VahanNetra-Webhook-Worker/1.0",
            },
        )
        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "idempotency_key": idempotency_key,
            "retries": self.request.retries,
        }
    except requests.RequestException as exc:
        if self.request.retries >= self.max_retries:
            record_webhook_dead_letter.delay(
                {
                    "organization_id": organization_id,
                    "webhook_id": webhook_id,
                    "event_type": event_type,
                    "target_url": target_url,
                    "payload": payload,
                    "signature": signature,
                    "idempotency_key": idempotency_key,
                    "error": str(exc),
                    "retries": self.request.retries,
                }
            )
            raise
        countdown = min(2 ** (self.request.retries + 1), 60)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(name="app.tasks.webhooks.record_webhook_dead_letter")
def record_webhook_dead_letter(event: dict) -> dict:
    db = SessionLocal()
    try:
        record = WebhookDeadLetter(
            organization_id=str(event.get("organization_id", "")),
            webhook_id=str(event.get("webhook_id", "")),
            target_url=str(event.get("target_url", "")),
            event_type=str(event.get("event_type", "inspection.completed")),
            payload_json=json.dumps(event.get("payload", {})),
            signature=str(event.get("signature", "")),
            idempotency_key=str(event.get("idempotency_key", "")),
            error_message=str(event.get("error", "")),
            retries=int(event.get("retries", 0)),
            status="open",
        )
        db.add(record)
        db.commit()
        logger.error("webhook_delivery_dead_letter", extra={"event": event})
        return {"recorded": True, "id": record.id, "event": event}
    finally:
        db.close()
