# ============================================================
# DevAgent — Multi-Agent Orchestration System
# src/db/session.py — Async SQLAlchemy Engine & Session Factory
# ============================================================
# This module manages the async database connection lifecycle:
#
#   - Creates and configures the async SQLAlchemy engine
#   - Provides a session factory for scoped database operations
#   - Exposes a FastAPI dependency for request-scoped sessions
#   - Handles startup initialization and graceful shutdown
#
# Connection pooling is configured from settings.py:
#   POSTGRES_POOL_SIZE      → Maximum persistent connections
#   POSTGRES_MAX_OVERFLOW   → Burst connections under load
#   POSTGRES_POOL_TIMEOUT   → Seconds to wait for a connection
#
# Usage:
#   # FastAPI dependency injection
#   @app.get("/tasks")
#   async def list_tasks(session: AsyncSession = Depends(get_async_session)):
#       result = await session.execute(select(TaskRecord))
#       return result.scalars().all()
#
#   # Manual session management
#   async with async_session_factory() as session:
#       task = TaskRecord(description="...")
#       session.add(task)
#       await session.commit()
# ============================================================

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings
from src.models.database import Base

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Module-level state (initialized on startup, closed on shutdown)
# ----------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


# ==========================================================
# ENGINE CREATION — Async PostgreSQL connection pool
# ==========================================================

def _create_engine() -> AsyncEngine:
    """
    Create and configure the async SQLAlchemy engine.

    Reads connection URL and pool settings from the application
    settings singleton. Uses asyncpg as the async PostgreSQL driver.

    Returns:
        Configured AsyncEngine instance
    """
    settings = get_settings()
    database_url = settings.database_url_computed

    engine = create_async_engine(
        database_url,
        # --- Connection Pool ---
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
        pool_pre_ping=True,         # Verify connections before checkout
        pool_recycle=3600,          # Recycle connections after 1 hour

        # --- Query Execution ---
        echo=settings.APP_DEBUG,    # Log SQL in debug mode
        echo_pool=False,            # Don't log pool events (too noisy)

        # --- Connection Args ---
        connect_args={
            "server_settings": {
                "application_name": settings.APP_NAME,
                "jit": "off",       # Disable JIT for faster short queries
            },
        },
    )

    logger.info(
        "Database engine created",
        extra={
            "pool_size": settings.POSTGRES_POOL_SIZE,
            "max_overflow": settings.POSTGRES_MAX_OVERFLOW,
            "echo": settings.APP_DEBUG,
        },
    )

    return engine


def _create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session factory bound to the given engine.

    Sessions created by this factory:
    - Are NOT auto-committed (explicit commit required)
    - Are NOT auto-flushed (explicit flush or commit required)
    - Expire objects on commit (forces refresh on next access)

    Args:
        engine: The async engine to bind sessions to

    Returns:
        Configured async_sessionmaker instance
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=True,
        autocommit=False,
        autoflush=False,
    )


# ==========================================================
# LIFECYCLE — Startup and shutdown hooks
# ==========================================================

async def init_db() -> None:
    """
    Initialize the database engine and session factory.

    Call this during application startup (FastAPI lifespan).
    Creates all tables if they don't exist (development only —
    use Alembic migrations in production).
    """
    global _engine, _session_factory

    _engine = _create_engine()
    _session_factory = _create_session_factory(_engine)

    settings = get_settings()

    # In development, auto-create tables for convenience.
    # In production, rely on Alembic migrations.
    if settings.is_development:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified (development mode)")

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """
    Gracefully shut down the database engine.

    Call this during application shutdown to properly close
    all connections in the pool and release resources.
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")

    _engine = None
    _session_factory = None


# ==========================================================
# SESSION ACCESS — Getting sessions for database operations
# ==========================================================

def get_engine() -> AsyncEngine:
    """
    Get the current async engine instance.

    Raises:
        RuntimeError: If the database hasn't been initialized yet
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_db() first. "
            "This typically happens in FastAPI's lifespan startup."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the current session factory.

    Raises:
        RuntimeError: If the database hasn't been initialized yet
    """
    if _session_factory is None:
        raise RuntimeError(
            "Session factory not initialized. Call init_db() first."
        )
    return _session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a request-scoped async session.

    The session is automatically committed on success and rolled
    back on exception. Always closed when the request finishes.

    Usage:
        @app.post("/tasks")
        async def create_task(
            task: TaskCreate,
            session: AsyncSession = Depends(get_async_session),
        ):
            record = TaskRecord(**task.model_dump())
            session.add(record)
            await session.commit()
            return record
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_managed_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for non-FastAPI code (background tasks, scripts).

    Provides the same commit/rollback/close semantics as the
    FastAPI dependency, but usable with `async with`:

    Usage:
        async with get_managed_session() as session:
            task = TaskRecord(description="...")
            session.add(task)
            # Auto-committed on exit, rolled back on exception
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
