# ============================================================
# DevAgent — Multi-Agent Orchestration System
# src/db/redis_client.py — Async Redis Client
# ============================================================
# This module manages the async Redis connection lifecycle:
#
#   - Creates and configures the async Redis client with pooling
#   - Provides key-prefixed operations for namespace isolation
#   - Exposes convenience methods for common patterns:
#       - Key/value storage with TTL
#       - JSON serialization/deserialization
#       - Atomic counters (rate limiting)
#       - Hash operations (session/context storage)
#   - Handles startup initialization and graceful shutdown
#
# Redis is used by DevAgent for:
#   - Shared agent memory (cross-agent context passing)
#   - Session cache (user sessions, conversation state)
#   - Rate limiting (API and LLM request throttling)
#   - Task status pub/sub (real-time WebSocket updates)
#
# Usage:
#   from src.db.redis_client import get_redis_client
#
#   redis = get_redis_client()
#   await redis.set_json("task:123", {"status": "executing"})
#   data = await redis.get_json("task:123")
# ============================================================

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from src.config.constants import (
    RATE_LIMIT_KEY_PREFIX,
    SESSION_KEY_PREFIX,
    SHARED_MEMORY_KEY_PREFIX,
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Module-level state
# ----------------------------------------------------------
_redis_client: RedisClient | None = None


# ==========================================================
# REDIS CLIENT — Async wrapper with convenience methods
# ==========================================================


class RedisClient:
    """
    Async Redis client wrapper with connection pooling and
    namespace-aware key operations.

    This class wraps the raw redis.asyncio.Redis client to provide:
    - Automatic key prefixing for namespace isolation
    - JSON serialization/deserialization for complex values
    - Typed convenience methods for common patterns
    - Health check capability

    All keys are automatically prefixed to prevent collisions
    between DevAgent subsystems (memory, sessions, rate limits).
    """

    def __init__(self, client: Redis) -> None:
        """
        Initialize with an existing async Redis client.

        Args:
            client: Configured redis.asyncio.Redis instance
        """
        self._client = client

    @property
    def client(self) -> Redis:
        """Access the underlying Redis client for advanced operations."""
        return self._client

    # ----------------------------------------------------------
    # HEALTH CHECK
    # ----------------------------------------------------------

    async def ping(self) -> bool:
        """
        Check if Redis is reachable.

        Returns:
            True if Redis responds to PING, False otherwise
        """
        try:
            return await self._client.ping()
        except Exception:
            return False

    # ----------------------------------------------------------
    # BASIC KEY/VALUE OPERATIONS
    # ----------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """
        Get a string value by key.

        Args:
            key: The key to look up

        Returns:
            The string value, or None if key doesn't exist
        """
        result = await self._client.get(key)
        if result is None:
            return None
        return result.decode("utf-8") if isinstance(result, bytes) else result

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """
        Set a string value with optional TTL.

        Args:
            key: The key to set
            value: String value to store
            ttl: Time-to-live in seconds (None = no expiry)

        Returns:
            True if set successfully
        """
        if ttl is not None:
            return bool(await self._client.setex(key, ttl, value))
        return bool(await self._client.set(key, value))

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Returns:
            Number of keys that were deleted
        """
        if not keys:
            return 0
        result = await self._client.delete(*keys)
        return result

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        result = await self._client.exists(key)
        return bool(result)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set a TTL on an existing key."""
        result = await self._client.expire(key, ttl)
        return result

    async def ttl(self, key: str) -> int:
        """
        Get the remaining TTL of a key in seconds.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        result = await self._client.ttl(key)
        return result

    # ----------------------------------------------------------
    # JSON OPERATIONS — Store/retrieve complex objects
    # ----------------------------------------------------------

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        """
        Get a JSON-serialized value and deserialize it.

        Args:
            key: The key to look up

        Returns:
            Deserialized Python dict/list, or None if key doesn't exist
        """
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            result = json.loads(raw)
            if isinstance(result, (dict, list)):
                return result
            return None
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to decode JSON for key: %s", key)
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list[Any],
        ttl: int | None = None,
    ) -> bool:
        """
        Serialize a dict/list as JSON and store it.

        Args:
            key: The key to set
            value: Dict or list to JSON-serialize and store
            ttl: Time-to-live in seconds (None = no expiry)

        Returns:
            True if set successfully
        """
        serialized = json.dumps(value, default=str)
        return await self.set(key, serialized, ttl=ttl)

    # ----------------------------------------------------------
    # HASH OPERATIONS — For structured session/context storage
    # ----------------------------------------------------------

    async def hget(self, name: str, key: str) -> str | None:
        """Get a single field from a hash."""
        result = await self._client.hget(name, key)
        if result is None:
            return None
        return result.decode("utf-8") if isinstance(result, bytes) else result

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set a single field in a hash."""
        result = await self._client.hset(name, key, value)
        return result

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all fields and values from a hash."""
        result = await self._client.hgetall(name)
        return {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in result.items()
        }

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete one or more fields from a hash."""
        if not keys:
            return 0
        result = await self._client.hdel(name, *keys)
        return result

    # ----------------------------------------------------------
    # COUNTER OPERATIONS — For rate limiting
    # ----------------------------------------------------------

    async def incr(self, key: str) -> int:
        """Atomically increment a counter. Creates key with value 1 if missing."""
        result = await self._client.incr(key)
        return result

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        """
        Atomically increment a counter and set TTL if key is new.

        Used for sliding-window rate limiting:
            count = await redis.incr_with_ttl("ratelimit:user:123", ttl=60)
            if count > MAX_REQUESTS:
                raise RateLimitExceeded()

        Args:
            key: Counter key
            ttl: TTL in seconds (only applied on first increment)

        Returns:
            Current counter value after increment
        """
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()

        count = int(results[0])
        current_ttl = int(results[1])

        # Set TTL only if the key has no expiry (newly created)
        if current_ttl == -1:
            await self._client.expire(key, ttl)

        return count

    # ----------------------------------------------------------
    # SHARED MEMORY — Cross-agent context passing
    # ----------------------------------------------------------

    async def set_shared_memory(
        self,
        task_id: str,
        key: str,
        value: dict[str, Any] | list[Any],
        ttl: int | None = None,
    ) -> bool:
        """
        Store shared context for cross-agent communication.

        When one agent's output is needed by another (e.g., Research
        findings used by Coding agent), store it here.

        Args:
            task_id: Parent task ID
            key: Context key (e.g., "research_findings")
            value: Data to share
            ttl: Optional TTL (defaults to REDIS_SESSION_TTL)
        """
        settings = get_settings()
        full_key = f"{SHARED_MEMORY_KEY_PREFIX}{task_id}:{key}"
        effective_ttl = ttl or settings.REDIS_SESSION_TTL
        return await self.set_json(full_key, value, ttl=effective_ttl)

    async def get_shared_memory(
        self,
        task_id: str,
        key: str,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Retrieve shared context for cross-agent communication.

        Args:
            task_id: Parent task ID
            key: Context key

        Returns:
            Stored data or None if not found
        """
        full_key = f"{SHARED_MEMORY_KEY_PREFIX}{task_id}:{key}"
        return await self.get_json(full_key)

    # ----------------------------------------------------------
    # SESSION MANAGEMENT
    # ----------------------------------------------------------

    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Store session data with configurable TTL."""
        settings = get_settings()
        full_key = f"{SESSION_KEY_PREFIX}{session_id}"
        effective_ttl = ttl or settings.REDIS_SESSION_TTL
        return await self.set_json(full_key, data, ttl=effective_ttl)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data."""
        full_key = f"{SESSION_KEY_PREFIX}{session_id}"
        result = await self.get_json(full_key)
        return result if isinstance(result, dict) else None

    async def delete_session(self, session_id: str) -> int:
        """Delete a session."""
        full_key = f"{SESSION_KEY_PREFIX}{session_id}"
        return await self.delete(full_key)

    # ----------------------------------------------------------
    # RATE LIMITING
    # ----------------------------------------------------------

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if a rate limit has been exceeded.

        Uses a sliding-window counter pattern.

        Args:
            identifier: Rate limit key (e.g., "api:user:123" or "llm:global")
            max_requests: Maximum allowed requests in the window
            window_seconds: Window duration in seconds

        Returns:
            Tuple of (is_allowed, current_count)
        """
        full_key = f"{RATE_LIMIT_KEY_PREFIX}{identifier}"
        count = await self.incr_with_ttl(full_key, window_seconds)
        is_allowed = count <= max_requests
        return is_allowed, count

    # ----------------------------------------------------------
    # CLEANUP
    # ----------------------------------------------------------

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.aclose()
        logger.info("Redis connection closed")


# ==========================================================
# LIFECYCLE — Startup and shutdown hooks
# ==========================================================


async def init_redis() -> None:
    """
    Initialize the Redis client with connection pooling.

    Call this during application startup (FastAPI lifespan).
    Reads connection URL from settings.
    """
    global _redis_client

    settings = get_settings()
    redis_url = settings.redis_url_computed

    pool = ConnectionPool.from_url(
        redis_url,
        max_connections=settings.POSTGRES_POOL_SIZE * 2,  # More Redis conns than PG
        decode_responses=False,  # We handle decoding ourselves
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )

    client = Redis(connection_pool=pool)
    _redis_client = RedisClient(client)

    # Verify connectivity
    if await _redis_client.ping():
        logger.info("Redis connected successfully", extra={"url": redis_url.split("@")[-1]})
    else:
        logger.warning("Redis PING failed — cache operations will error")


async def close_redis() -> None:
    """
    Gracefully shut down the Redis client.

    Call this during application shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        logger.info("Redis client closed")

    _redis_client = None


# ==========================================================
# CLIENT ACCESS
# ==========================================================


def get_redis_client() -> RedisClient:
    """
    Get the current Redis client instance.

    Raises:
        RuntimeError: If Redis hasn't been initialized yet

    Usage:
        redis = get_redis_client()
        await redis.set_json("key", {"data": "value"})
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. Call init_redis() first. "
            "This typically happens in FastAPI's lifespan startup."
        )
    return _redis_client
