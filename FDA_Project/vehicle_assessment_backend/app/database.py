import os
from pathlib import Path
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv(
    "VAHANNETRA_DB_PATH", settings.db_path or str(BASE_DIR / "vahannetra.db")
)
DATABASE_URL = os.getenv(
    "VAHANNETRA_DATABASE_URL", settings.database_url or f"sqlite:///{DB_PATH}"
)


def _derive_async_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


ASYNC_DATABASE_URL = os.getenv(
    "VAHANNETRA_ASYNC_DATABASE_URL", _derive_async_database_url(DATABASE_URL)
)

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=(
        {"check_same_thread": False}
        if ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite")
        else {}
    ),
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def apply_rls_policies() -> None:
    if not is_postgres():
        return

    rls_sql = """
    ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
    ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
    ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    ALTER TABLE otp_delivery_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE client_error_events ENABLE ROW LEVEL SECURITY;

    ALTER TABLE inspections FORCE ROW LEVEL SECURITY;
    ALTER TABLE claims FORCE ROW LEVEL SECURITY;
    ALTER TABLE settings FORCE ROW LEVEL SECURITY;
    ALTER TABLE users FORCE ROW LEVEL SECURITY;
    ALTER TABLE otp_delivery_events FORCE ROW LEVEL SECURITY;
    ALTER TABLE client_error_events FORCE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS inspections_org_scope ON inspections;
    DROP POLICY IF EXISTS claims_org_scope ON claims;
    DROP POLICY IF EXISTS settings_org_scope ON settings;
    DROP POLICY IF EXISTS users_org_scope ON users;
    DROP POLICY IF EXISTS otp_delivery_events_org_scope ON otp_delivery_events;
    DROP POLICY IF EXISTS client_error_events_org_scope ON client_error_events;

    CREATE POLICY inspections_org_scope
      ON inspections
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));

    CREATE POLICY claims_org_scope
      ON claims
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));

    CREATE POLICY settings_org_scope
      ON settings
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));

    CREATE POLICY users_org_scope
      ON users
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));

    CREATE POLICY otp_delivery_events_org_scope
      ON otp_delivery_events
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));

    CREATE POLICY client_error_events_org_scope
      ON client_error_events
      USING (organization_id = current_setting('app.current_org_id', true))
      WITH CHECK (organization_id = current_setting('app.current_org_id', true));
    """
    statements = [line.strip() for line in rls_sql.split(";") if line.strip()]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def set_org_context(db: Session, organization_id: str) -> None:
    if not is_postgres():
        return
    db.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": organization_id},
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
