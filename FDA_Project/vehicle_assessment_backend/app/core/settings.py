import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    db_path: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    refresh_token_days: int
    redis_url: str
    celery_queue: str
    celery_dlq_queue: str
    celery_visibility_timeout_seconds: int
    celery_soft_time_limit_seconds: int
    celery_hard_time_limit_seconds: int
    s3_bucket: str
    integration_mode: str
    integration_timeout_seconds: float
    integration_max_retries: int
    integration_circuit_failures: int
    integration_circuit_recovery_seconds: int
    vahan_base_url: str
    insurer_base_url: str


BASE_DIR = Path(__file__).resolve().parent.parent.parent
_default_db_path = str(BASE_DIR / "vahannetra.db")

settings = Settings(
    app_name=os.getenv("VAHANNETRA_APP_NAME", "AI Vehicle Assessment Backend"),
    db_path=os.getenv("VAHANNETRA_DB_PATH", _default_db_path),
    database_url=os.getenv(
        "VAHANNETRA_DATABASE_URL",
        f"sqlite:///{os.getenv('VAHANNETRA_DB_PATH', _default_db_path)}",
    ),
    jwt_secret=os.getenv(
        "VAHANNETRA_JWT_SECRET", "change-me-in-production-very-long-secret-key-32chars"
    ),
    jwt_algorithm=os.getenv("VAHANNETRA_JWT_ALGORITHM", "HS256"),
    access_token_minutes=int(os.getenv("VAHANNETRA_ACCESS_TOKEN_MINUTES", "30")),
    refresh_token_days=int(os.getenv("VAHANNETRA_REFRESH_TOKEN_DAYS", "14")),
    redis_url=os.getenv("VAHANNETRA_REDIS_URL", "redis://redis:6379/0"),
    celery_queue=os.getenv("VAHANNETRA_CELERY_QUEUE", "vehicle_assessment"),
    celery_dlq_queue=os.getenv("VAHANNETRA_CELERY_DLQ_QUEUE", "vehicle_assessment_dlq"),
    celery_visibility_timeout_seconds=int(
        os.getenv("VAHANNETRA_CELERY_VISIBILITY_TIMEOUT_SECONDS", "3600")
    ),
    celery_soft_time_limit_seconds=int(
        os.getenv("VAHANNETRA_CELERY_SOFT_TIME_LIMIT_SECONDS", "20")
    ),
    celery_hard_time_limit_seconds=int(
        os.getenv("VAHANNETRA_CELERY_HARD_TIME_LIMIT_SECONDS", "30")
    ),
    s3_bucket=os.getenv("VAHANNETRA_S3_BUCKET", "vahannetra-artifacts"),
    integration_mode=os.getenv("VAHANNETRA_INTEGRATION_MODE", "mock"),
    integration_timeout_seconds=float(
        os.getenv("VAHANNETRA_INTEGRATION_TIMEOUT_SECONDS", "5")
    ),
    integration_max_retries=int(os.getenv("VAHANNETRA_INTEGRATION_MAX_RETRIES", "2")),
    integration_circuit_failures=int(
        os.getenv("VAHANNETRA_INTEGRATION_CIRCUIT_FAILURES", "3")
    ),
    integration_circuit_recovery_seconds=int(
        os.getenv("VAHANNETRA_INTEGRATION_CIRCUIT_RECOVERY_SECONDS", "30")
    ),
    vahan_base_url=os.getenv("VAHANNETRA_VAHAN_BASE_URL", "https://vahan.example"),
    insurer_base_url=os.getenv(
        "VAHANNETRA_INSURER_BASE_URL", "https://insurer.example"
    ),
)
