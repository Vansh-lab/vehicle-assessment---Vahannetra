from __future__ import annotations

from vahannetra.backend.app.tasks.celery_app import celery_app


@celery_app.task(name="vahannetra.phase3.pipeline.process_job")
def process_job(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "status": "queued"}


def enqueue_pipeline(job_id: str) -> str:
    try:
        process_job.delay(job_id)
        return "dispatched"
    except Exception:
        return "deferred"
