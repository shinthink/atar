"""ATAR storage engine — SQLAlchemy async + SQLite WAL per ADR-003."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(db_path: str = "data/atar.sqlite3") -> AsyncEngine:
    """Create async SQLite engine with WAL mode."""
    import os
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
