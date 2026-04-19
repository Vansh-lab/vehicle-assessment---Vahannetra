from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from vahannetra.backend.app.core.settings import settings


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(
    settings.async_database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.async_database_url.startswith("sqlite+aiosqlite")
        else {}
    ),
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def init_models() -> None:
    from vahannetra.backend.app import models  # noqa: F401

    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
