"""Pydantic contracts shared by the API, orchestration, and persistence layers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config.constants import AgentType, Priority, SubTaskStatus, TaskStatus


class TaskCreate(BaseModel):
    description: str = Field(min_length=1, max_length=10_000)
    priority: Priority = Priority.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("description cannot be blank")
        return value


class SubTaskPlan(BaseModel):
    subtask_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(min_length=1)
    agent_type: AgentType
    order: int = Field(ge=0)
    dependencies: list[str] = Field(default_factory=list)
    tools_required: list[str] = Field(default_factory=list)


class SubTaskResult(BaseModel):
    subtask_id: str
    agent_type: AgentType
    output: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)
    token_count: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    status: SubTaskStatus = SubTaskStatus.COMPLETED
    error: str | None = None


class TaskResult(BaseModel):
    output: str
    confidence: float = Field(ge=0.0, le=1.0)
    subtask_results: list[SubTaskResult] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    total_tokens: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0.0)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: UUID | str
    description: str
    status: TaskStatus
    priority: Priority = Priority.MEDIUM
    result: TaskResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
