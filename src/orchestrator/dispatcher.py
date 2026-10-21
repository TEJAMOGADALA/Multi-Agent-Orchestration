"""Dependency-aware concurrent scheduler for specialized agents."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.agents.registry import AgentRegistry
from src.config.constants import AgentType, SubTaskStatus
from src.config.settings import get_settings
from src.models.database import AgentMetric, ExecutionLog, SubTaskRecord
from src.models.state import OrchestratorState, create_agent_state


class DispatcherNode:
    def __init__(self, *, agent_registry: type[AgentRegistry] = AgentRegistry) -> None:
        self.agent_registry = agent_registry
        settings = get_settings()
        self.max_concurrency = settings.AGENT_MAX_CONCURRENCY
        self.max_retries = settings.AGENT_MAX_RETRIES

    @staticmethod
    def _resolve_ready_subtasks(state: OrchestratorState) -> list[str]:
        finished = set(state.get("completed_subtasks", []))
        return [
            subtask_id
            for subtask_id in state.get("pending_subtasks", [])
            if set(state["subtask_states"][subtask_id].get("dependencies", [])) <= finished
        ]

    @staticmethod
    def _shared_context(state: OrchestratorState, dependencies: list[str]) -> dict[str, Any]:
        results = {item["subtask_id"]: item for item in state.get("subtask_results", [])}
        return {
            dependency: results[dependency].get("output", "")
            for dependency in dependencies
            if dependency in results
        }

    async def _execute_agent(
        self, state: OrchestratorState, subtask_id: str, semaphore: asyncio.Semaphore
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        subtask = state["subtask_states"][subtask_id]
        async with semaphore:
            agent = self.agent_registry.create_agent(AgentType(subtask["agent_type"]))
            agent_state = create_agent_state(
                task_id=state["task_id"],
                subtask_id=subtask_id,
                agent_type=subtask["agent_type"],
                subtask_description=subtask["description"],
                shared_context=self._shared_context(state, subtask.get("dependencies", [])),
            )
            completed = await agent.invoke(agent_state)
            return subtask_id, dict(completed.get("result") or {}), dict(completed)

    async def dispatch_subtasks(self, state: OrchestratorState) -> dict[str, Any]:
        """Run every currently unblocked DAG level, retrying failed work in place."""
        states = {key: dict(value) for key, value in state.get("subtask_states", {}).items()}
        pending = list(state.get("pending_subtasks", []))
        completed = list(state.get("completed_subtasks", []))
        failed = list(state.get("failed_subtasks", []))
        results = list(state.get("subtask_results", []))
        semaphore = asyncio.Semaphore(self.max_concurrency)

        while pending:
            local_state: OrchestratorState = {
                **state,
                "subtask_states": states,
                "pending_subtasks": pending,
                "completed_subtasks": completed,
                "subtask_results": results,
            }
            ready = self._resolve_ready_subtasks(local_state)
            if not ready:
                failed.extend(item for item in pending if item not in failed)
                break
            for subtask_id in ready:
                pending.remove(subtask_id)
                states[subtask_id]["status"] = SubTaskStatus.IN_PROGRESS.value
            executions = await asyncio.gather(
                *(self._execute_agent(local_state, subtask_id, semaphore) for subtask_id in ready),
                return_exceptions=True,
            )
            for expected_id, execution in zip(ready, executions, strict=True):
                result: dict[str, Any]
                raw: dict[str, Any]
                if isinstance(execution, BaseException):
                    subtask_id, result, raw = expected_id, {}, {"error": str(execution)}
                else:
                    subtask_id, result, raw = execution
                if result and result.get("status") == SubTaskStatus.COMPLETED.value:
                    states[subtask_id]["status"] = SubTaskStatus.COMPLETED.value
                    completed.append(subtask_id)
                    results.append(result)
                    await self._persist_outcome(state["task_id"], subtask_id, result)
                else:
                    states[subtask_id]["retry_count"] = states[subtask_id].get("retry_count", 0) + 1
                    if states[subtask_id]["retry_count"] <= self.max_retries:
                        states[subtask_id]["status"] = SubTaskStatus.PENDING.value
                        pending.append(subtask_id)
                    else:
                        states[subtask_id]["status"] = SubTaskStatus.FAILED.value
                        states[subtask_id]["error"] = result.get("error") or raw.get(
                            "error", "agent failed"
                        )
                        failed.append(subtask_id)
                        await self._persist_outcome(
                            state["task_id"], subtask_id, result, states[subtask_id]["error"]
                        )
        return {
            "subtask_states": states,
            "pending_subtasks": pending,
            "completed_subtasks": completed,
            "failed_subtasks": failed,
            "subtask_results": results,
        }

    async def _persist_outcome(
        self, task_id: str, subtask_id: str, result: dict[str, Any], error: str | None = None
    ) -> None:
        try:
            from src.db.session import get_managed_session

            async with get_managed_session() as session:
                task_uuid = UUID(task_id)
                record = await session.get(SubTaskRecord, subtask_id)
                if record:
                    record.status = (
                        SubTaskStatus.FAILED.value if error else SubTaskStatus.COMPLETED.value
                    )
                    record.result = result or None
                usage = result or {}
                session.add(
                    AgentMetric(
                        task_id=task_uuid,
                        subtask_id=subtask_id,
                        prompt_tokens=0,
                        completion_tokens=usage.get("token_count", 0),
                        cost_usd=usage.get("cost_usd", 0.0),
                        duration_seconds=usage.get("duration_seconds", 0.0),
                    )
                )
                session.add(
                    ExecutionLog(
                        task_id=task_uuid,
                        subtask_id=subtask_id,
                        event="agent_failed" if error else "agent_completed",
                        detail={"error": error} if error else {},
                    )
                )
        except RuntimeError:
            return
