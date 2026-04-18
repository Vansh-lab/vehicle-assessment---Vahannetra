from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    api_prefix: str
    database_url: str
    async_database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    redis_url: str
    celery_broker_url: str
    allowed_origins: tuple[str, ...]


_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_DB = _REPO_ROOT / "vahannetra" / "backend" / "vahannetra_phase2.db"
_DEV_JWT_SECRET = "vahannetra-phase2-dev-secret"


def _derive_async_db_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + database_url.removeprefix("sqlite:///")
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql+"):
        scheme, remainder = database_url.split("://", 1)
        return f"postgresql+asyncpg://{remainder}"
    return database_url


settings = Settings(
    app_name=os.getenv("VAHANNETRA_PHASE2_APP_NAME", "VahanNetra Backend Foundation"),
    app_env=os.getenv("VAHANNETRA_PHASE2_ENV", "development"),
    api_prefix=os.getenv("VAHANNETRA_PHASE2_API_PREFIX", "/api/v1"),
    database_url=os.getenv("VAHANNETRA_PHASE2_DATABASE_URL", f"sqlite:///{_DEFAULT_DB}"),
    async_database_url=os.getenv(
        "VAHANNETRA_PHASE2_ASYNC_DATABASE_URL",
        _derive_async_db_url(
            os.getenv("VAHANNETRA_PHASE2_DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")
        ),
    ),
    jwt_secret=os.getenv("VAHANNETRA_PHASE2_JWT_SECRET", _DEV_JWT_SECRET),
    jwt_algorithm=os.getenv("VAHANNETRA_PHASE2_JWT_ALGORITHM", "HS256"),
    access_token_minutes=int(os.getenv("VAHANNETRA_PHASE2_ACCESS_TOKEN_MINUTES", "30")),
    redis_url=os.getenv("VAHANNETRA_PHASE2_REDIS_URL", "redis://localhost:6379/0"),
    celery_broker_url=os.getenv(
        "VAHANNETRA_PHASE2_CELERY_BROKER_URL",
        os.getenv("VAHANNETRA_PHASE2_REDIS_URL", "redis://localhost:6379/0"),
    ),
    allowed_origins=tuple(
        item.strip()
        for item in os.getenv(
            "VAHANNETRA_PHASE2_ALLOWED_ORIGINS", "http://localhost:3000"
        ).split(",")
        if item.strip()
    ),
)

if settings.app_env != "development" and (
    not settings.jwt_secret or settings.jwt_secret == _DEV_JWT_SECRET
):
    raise RuntimeError(
        "VAHANNETRA_PHASE2_JWT_SECRET must be set for non-development environments."
    )
