# ============================================================
# DevAgent — Multi-Agent Orchestration System
# src/db/__init__.py — Database Package
# ============================================================
# This package contains all database connectivity modules:
#
#   session.py      — Async SQLAlchemy engine & session factory
#   redis_client.py — Async Redis client with connection pooling
#
# Usage:
#   from src.db.session import get_async_session, get_engine
#   from src.db.redis_client import get_redis_client
# ============================================================

# Imports will be added as modules are created in Steps 2.6-2.7.

from src.db.redis_client import RedisClient, close_redis, get_redis_client, init_redis
from src.db.session import (
    close_db,
    get_async_session,
    get_engine,
    get_managed_session,
    get_session_factory,
    init_db,
)

__all__ = [
    "RedisClient",
    "close_db",
    "close_redis",
    "get_async_session",
    "get_engine",
    "get_managed_session",
    "get_redis_client",
    "get_session_factory",
    # Session
    "init_db",
    # Redis
    "init_redis",
]
