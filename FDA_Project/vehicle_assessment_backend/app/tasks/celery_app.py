from __future__ import annotations

import os

from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

celery_app = Celery(
    "vahannetra_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.webhooks"],
)

celery_app.conf.update(
    task_default_queue=os.getenv("VAHANNETRA_CELERY_QUEUE", "vehicle_assessment"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
