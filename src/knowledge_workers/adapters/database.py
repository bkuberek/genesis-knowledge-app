"""Async database engine, session factory, and RLS context setter."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from knowledge_core.config import settings


def build_database_url() -> str:
    """Build PostgreSQL async connection URL from settings."""
    return (
        f"postgresql+asyncpg://{settings.database.user}"
        f":{settings.database.password}"
        f"@{settings.database.host}"
        f":{settings.database.port}"
        f"/{settings.database.name}"
    )


def create_engine() -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(
        build_database_url(),
        echo=settings.get("debug", False),
        pool_size=10,
        max_overflow=20,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def set_rls_context(
    session: AsyncSession,
    user_id: str,
) -> None:
    """Set the current user ID for Row-Level Security policies."""
    await session.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(user_id)},
    )
