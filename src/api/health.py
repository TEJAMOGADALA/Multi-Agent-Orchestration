"""Liveness and dependency-readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.constants import HEALTH_ENDPOINT, READY_ENDPOINT

router = APIRouter(tags=["health"])


@router.get(HEALTH_ENDPOINT)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(READY_ENDPOINT)
async def ready() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        from src.db.session import get_engine

        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
    try:
        from src.db.redis_client import get_redis_client

        checks["redis"] = "ok" if await get_redis_client().ping() else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"
    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        {"status": "ready" if is_ready else "degraded", "checks": checks},
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
