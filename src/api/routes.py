"""Authenticated REST endpoints for asynchronous task submission and status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import TaskRuntime, get_task_runtime, require_api_key
from src.models.schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"], dependencies=[Depends(require_api_key)])
runtime_dependency = Depends(get_task_runtime)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(task: TaskCreate, runtime: TaskRuntime = runtime_dependency) -> TaskResponse:
    return await runtime.submit(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, runtime: TaskRuntime = runtime_dependency) -> TaskResponse:
    response = await runtime.get(task_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return response


@router.delete("/{task_id}", response_model=TaskResponse)
async def cancel_task(task_id: str, runtime: TaskRuntime = runtime_dependency) -> TaskResponse:
    response = await runtime.cancel(task_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return response


@router.get("/{task_id}/result", response_model=TaskResponse)
async def get_result(task_id: str, runtime: TaskRuntime = runtime_dependency) -> TaskResponse:
    response = await runtime.get(task_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    if not response.status.is_terminal:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="task is still running")
    return response
