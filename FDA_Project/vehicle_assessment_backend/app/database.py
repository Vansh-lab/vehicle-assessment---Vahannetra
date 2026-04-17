import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("VAHANNETRA_DB_PATH", str(BASE_DIR / "vahannetra.db"))
DATABASE_URL = os.getenv("VAHANNETRA_DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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

    ALTER TABLE inspections FORCE ROW LEVEL SECURITY;
    ALTER TABLE claims FORCE ROW LEVEL SECURITY;
    ALTER TABLE settings FORCE ROW LEVEL SECURITY;
    ALTER TABLE users FORCE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS inspections_org_scope ON inspections;
    DROP POLICY IF EXISTS claims_org_scope ON claims;
    DROP POLICY IF EXISTS settings_org_scope ON settings;
    DROP POLICY IF EXISTS users_org_scope ON users;

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
    """
    statements = [line.strip() for line in rls_sql.split(";") if line.strip()]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def set_org_context(db: Session, organization_id: str) -> None:
    if not is_postgres():
        return
    db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": organization_id})


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
