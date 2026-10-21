"""Gateway safeguards: request-size cap, Redis rate limit, and safe error responses."""

from __future__ import annotations

import hashlib
import logging

from fastapi import FastAPI, Request  # noqa: TC002 - used by FastAPI's runtime decorator.
from fastapi.responses import JSONResponse

from src.config.constants import API_V1_PREFIX
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard_request(request: Request, call_next: object) -> object:
        if not request.url.path.startswith(API_V1_PREFIX):
            return await call_next(request)  # type: ignore[misc]
        settings = get_settings()
        maximum = settings.MAX_REQUEST_SIZE_MB * 1024 * 1024
        if int(request.headers.get("content-length", 0) or 0) > maximum:
            return JSONResponse({"detail": "request body is too large"}, status_code=413)
        body = await request.body()
        if len(body) > maximum:
            return JSONResponse({"detail": "request body is too large"}, status_code=413)
        identifier = hashlib.sha256(
            request.headers.get("x-api-key", "anonymous").encode()
        ).hexdigest()
        try:
            from src.db.redis_client import get_redis_client

            allowed, _ = await get_redis_client().check_rate_limit(
                f"api:{identifier}",
                settings.RATE_LIMIT_REQUESTS,
                settings.RATE_LIMIT_WINDOW_SECONDS,
            )
        except Exception:
            return JSONResponse({"detail": "rate limiter unavailable"}, status_code=503)
        if not allowed:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        try:
            return await call_next(request)  # type: ignore[misc]
        except Exception:
            logger.exception("Unhandled API error")
            return JSONResponse({"detail": "internal server error"}, status_code=500)
