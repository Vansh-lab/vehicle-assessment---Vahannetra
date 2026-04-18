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
    s3_bucket: str


BASE_DIR = Path(__file__).resolve().parent.parent.parent
_default_db_path = str(BASE_DIR / "vahannetra.db")

settings = Settings(
    app_name=os.getenv("VAHANNETRA_APP_NAME", "AI Vehicle Assessment Backend"),
    db_path=os.getenv("VAHANNETRA_DB_PATH", _default_db_path),
    database_url=os.getenv("VAHANNETRA_DATABASE_URL", f"sqlite:///{os.getenv('VAHANNETRA_DB_PATH', _default_db_path)}"),
    jwt_secret=os.getenv("VAHANNETRA_JWT_SECRET", "change-me-in-production-very-long-secret-key-32chars"),
    jwt_algorithm=os.getenv("VAHANNETRA_JWT_ALGORITHM", "HS256"),
    access_token_minutes=int(os.getenv("VAHANNETRA_ACCESS_TOKEN_MINUTES", "30")),
    refresh_token_days=int(os.getenv("VAHANNETRA_REFRESH_TOKEN_DAYS", "14")),
    redis_url=os.getenv("VAHANNETRA_REDIS_URL", "redis://redis:6379/0"),
    celery_queue=os.getenv("VAHANNETRA_CELERY_QUEUE", "vehicle_assessment"),
    s3_bucket=os.getenv("VAHANNETRA_S3_BUCKET", "vahannetra-artifacts"),
)
