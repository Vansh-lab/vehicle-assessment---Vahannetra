from __future__ import annotations

import os

from celery import Celery

from vahannetra.backend.app.core.settings import settings

celery_app = Celery(
    "vahannetra_phase3_worker",
    broker=os.getenv("CELERY_BROKER_URL", settings.celery_broker_url),
    backend=os.getenv("CELERY_RESULT_BACKEND", settings.celery_result_backend),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
