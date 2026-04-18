from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vahannetra.backend.app.core.settings import settings

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


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
