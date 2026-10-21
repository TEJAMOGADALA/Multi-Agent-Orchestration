"""LangGraph state definitions and safe initial-state factories."""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4

from src.config.constants import AgentType, SubTaskStatus, TaskStatus


class AgentState(TypedDict, total=False):
    task_id: str
    subtask_id: str
    agent_type: AgentType | str
    subtask_description: str
    shared_context: dict[str, Any]
    messages: list[Any]
    tool_calls: list[dict[str, Any]]
    pending_tool_calls: list[dict[str, Any]]
    token_usage: list[dict[str, Any]]
    iteration_count: int
    max_iterations: int
    final_answer: str
    result: dict[str, Any]
    status: SubTaskStatus | str
    error: str | None


class OrchestratorState(TypedDict, total=False):
    task_id: str
    task_description: str
    priority: int
    status: TaskStatus | str
    plan: list[dict[str, Any]]
    subtask_states: dict[str, dict[str, Any]]
    pending_subtasks: list[str]
    active_subtasks: list[str]
    completed_subtasks: list[str]
    failed_subtasks: list[str]
    subtask_results: list[dict[str, Any]]
    planning_reasoning: str
    validation_errors: list[str]
    result: dict[str, Any] | None
    error: str | None
    total_tokens: int
    total_cost_usd: float


def create_agent_state(
    *,
    task_id: str,
    subtask_id: str,
    agent_type: AgentType | str,
    subtask_description: str,
    shared_context: dict[str, Any] | None = None,
    max_iterations: int = 10,
) -> AgentState:
    return {
        "task_id": task_id,
        "subtask_id": subtask_id,
        "agent_type": agent_type,
        "subtask_description": subtask_description,
        "shared_context": shared_context or {},
        "messages": [],
        "tool_calls": [],
        "pending_tool_calls": [],
        "token_usage": [],
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "status": SubTaskStatus.PENDING,
        "error": None,
    }


def create_orchestrator_state(
    *,
    task_description: str,
    task_id: str | None = None,
    priority: int = 3,
) -> OrchestratorState:
    return {
        "task_id": task_id or str(uuid4()),
        "task_description": task_description,
        "priority": priority,
        "status": TaskStatus.PENDING,
        "plan": [],
        "subtask_states": {},
        "pending_subtasks": [],
        "active_subtasks": [],
        "completed_subtasks": [],
        "failed_subtasks": [],
        "subtask_results": [],
        "planning_reasoning": "",
        "validation_errors": [],
        "result": None,
        "error": None,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
    }
