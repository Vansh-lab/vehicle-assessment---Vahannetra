from fastapi import APIRouter

from app.core.settings import settings
from app.tasks.pipeline import PIPELINE_STEPS

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/capabilities")
def capabilities():
    return {
        "app_name": settings.app_name,
        "pipeline_steps": PIPELINE_STEPS,
        "storage_bucket": settings.s3_bucket,
        "queue": settings.celery_queue,
        "queue_dlq": settings.celery_dlq_queue,
        "celery": {
            "visibility_timeout_seconds": settings.celery_visibility_timeout_seconds,
            "soft_time_limit_seconds": settings.celery_soft_time_limit_seconds,
            "hard_time_limit_seconds": settings.celery_hard_time_limit_seconds,
        },
        "integrations": {
            "mode": settings.integration_mode,
            "timeout_seconds": settings.integration_timeout_seconds,
            "max_retries": settings.integration_max_retries,
            "circuit_failures": settings.integration_circuit_failures,
            "circuit_recovery_seconds": settings.integration_circuit_recovery_seconds,
        },
    }
