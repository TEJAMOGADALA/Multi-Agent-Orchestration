"""Gateway dependencies and the small in-process task runtime."""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from src.config.constants import TaskStatus
from src.config.settings import get_settings
from src.models.schemas import TaskCreate, TaskResponse, TaskResult
from src.orchestrator.engine import OrchestratorEngine

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    if not any(
        secrets.compare_digest(api_key, candidate) for candidate in get_settings().api_keys_list
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid API key")
    return api_key


class TaskRuntime:
    """Tracks active tasks locally while PostgreSQL remains the durable source of truth."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskResponse] = {}
        self._background: dict[str, asyncio.Task[None]] = {}
        self._engine: OrchestratorEngine | None = None

    async def submit(self, task: TaskCreate) -> TaskResponse:
        task_id = str(uuid4())
        response = TaskResponse(
            task_id=task_id,
            description=task.description,
            priority=task.priority,
            status=TaskStatus.PENDING,
        )
        self._tasks[task_id] = response
        self._background[task_id] = asyncio.create_task(self._run(task_id, task))
        return response

    async def _run(self, task_id: str, task: TaskCreate) -> None:
        initial = self._tasks[task_id]
        self._tasks[task_id] = initial.model_copy(update={"status": TaskStatus.EXECUTING})
        try:
            self._engine = self._engine or OrchestratorEngine()
            result = await self._engine.run_task(task, task_id=task_id)
            self._tasks[task_id] = result.model_copy(update={"created_at": initial.created_at})
        except asyncio.CancelledError:
            self._tasks[task_id] = initial.model_copy(
                update={"status": TaskStatus.CANCELLED, "completed_at": datetime.now(UTC)}
            )
            raise
        except Exception as exc:
            self._tasks[task_id] = initial.model_copy(
                update={
                    "status": TaskStatus.FAILED,
                    "error": "task execution failed" if get_settings().is_production else str(exc),
                    "completed_at": datetime.now(UTC),
                }
            )
        finally:
            self._background.pop(task_id, None)

    async def get(self, task_id: str) -> TaskResponse | None:
        active = self._tasks.get(task_id)
        if active is not None:
            return active
        return await self._load_persisted(task_id)

    async def cancel(self, task_id: str) -> TaskResponse | None:
        task = self._background.get(task_id)
        response = self._tasks.get(task_id)
        if task is None or response is None or response.status.is_terminal:
            return response
        cancelled = response.model_copy(
            update={"status": TaskStatus.CANCELLED, "completed_at": datetime.now(UTC)}
        )
        self._tasks[task_id] = cancelled
        task.cancel()
        await self._persist_cancellation(task_id)
        return cancelled

    async def close(self) -> None:
        for task in self._background.values():
            task.cancel()
        if self._background:
            await asyncio.gather(*self._background.values(), return_exceptions=True)

    async def _load_persisted(self, task_id: str) -> TaskResponse | None:
        try:
            from uuid import UUID

            from src.db.session import get_managed_session
            from src.models.database import TaskRecord

            async with get_managed_session() as session:
                record = await session.get(TaskRecord, UUID(task_id))
            if record is None:
                return None
            result = TaskResult.model_validate(record.result) if record.result else None
            return TaskResponse(
                task_id=record.id,
                description=record.description,
                priority=record.priority,
                status=record.status,
                result=result,
                error=record.error,
                created_at=record.created_at,
                completed_at=record.completed_at,
            )
        except Exception:
            return None

    async def _persist_cancellation(self, task_id: str) -> None:
        try:
            from uuid import UUID

            from src.db.session import get_managed_session
            from src.models.database import TaskRecord

            async with get_managed_session() as session:
                record = await session.get(TaskRecord, UUID(task_id))
                if record:
                    record.status = TaskStatus.CANCELLED.value
                    record.completed_at = datetime.now(UTC)
        except Exception:
            return


def get_task_runtime(request: Request) -> TaskRuntime:
    return cast("TaskRuntime", request.app.state.task_runtime)


def get_websocket_runtime(websocket: Any) -> TaskRuntime:
    return cast("TaskRuntime", websocket.app.state.task_runtime)
