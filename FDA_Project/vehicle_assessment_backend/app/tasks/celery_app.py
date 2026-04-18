from __future__ import annotations

import os

from celery import Celery

from app.core.settings import settings

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")
)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

celery_app = Celery(
    "vahannetra_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.webhooks"],
)

celery_app.conf.update(
    task_default_queue=settings.celery_queue,
    task_routes={
        "app.tasks.webhooks.deliver_webhook": {"queue": settings.celery_queue},
        "app.tasks.webhooks.record_webhook_dead_letter": {
            "queue": settings.celery_dlq_queue
        },
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_soft_time_limit=settings.celery_soft_time_limit_seconds,
    task_time_limit=settings.celery_hard_time_limit_seconds,
    broker_transport_options={
        "visibility_timeout": settings.celery_visibility_timeout_seconds
    },
)
