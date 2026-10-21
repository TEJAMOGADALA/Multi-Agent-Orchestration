"""FastAPI application factory and dependency lifecycle."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket

from src.api.dependencies import TaskRuntime
from src.api.health import router as health_router
from src.api.middleware import install_middleware
from src.api.routes import router as task_router
from src.api.websockets import stream_task
from src.config.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.task_runtime = TaskRuntime()
    app.state.db_initialized = False
    app.state.redis_initialized = False
    try:
        from src.db.session import init_db

        await init_db()
        app.state.db_initialized = True
    except Exception:
        logger.exception("Database initialization failed; readiness will remain degraded")
    try:
        from src.db.redis_client import init_redis

        await init_redis()
        app.state.redis_initialized = True
    except Exception:
        logger.exception("Redis initialization failed; API requests will be rate-limit unavailable")
    try:
        yield
    finally:
        await app.state.task_runtime.close()
        if app.state.redis_initialized:
            from src.db.redis_client import close_redis

            await close_redis()
        if app.state.db_initialized:
            from src.db.session import close_db

            await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
    install_middleware(app)
    app.include_router(health_router)
    app.include_router(task_router)

    @app.websocket("/api/v1/tasks/{task_id}/stream")
    async def task_stream(websocket: WebSocket, task_id: str) -> None:
        await stream_task(websocket, task_id)

    return app


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:create_app", factory=True, host=settings.APP_HOST, port=settings.APP_PORT
    )
