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
    }
