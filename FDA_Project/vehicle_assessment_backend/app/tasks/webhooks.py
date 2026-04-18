from __future__ import annotations

import requests

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, retry_jitter=True, max_retries=5)
def deliver_webhook(self, target_url: str, payload: dict, signature: str) -> dict:
    response = requests.post(
        target_url,
        json=payload,
        timeout=8,
        headers={
            "Content-Type": "application/json",
            "X-VahanNetra-Signature": signature,
            "User-Agent": "VahanNetra-Webhook-Worker/1.0",
        },
    )
    response.raise_for_status()
    return {"status_code": response.status_code}
