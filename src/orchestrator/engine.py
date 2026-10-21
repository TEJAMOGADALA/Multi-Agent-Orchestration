"""Top-level Planner → Dispatcher → Validator → Synthesizer graph."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from functools import cached_property
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from src.config.constants import TaskStatus
from src.config.settings import get_settings
from src.models.database import TaskRecord
from src.models.schemas import SubTaskResult, TaskCreate, TaskResponse, TaskResult
from src.models.state import OrchestratorState, create_orchestrator_state
from src.orchestrator.dispatcher import DispatcherNode
from src.orchestrator.planner import PlannerNode


def build_orchestrator_graph(planner: PlannerNode, dispatcher: DispatcherNode) -> Any:
    """Build a reusable graph; nodes return partial state to retain auditability."""

    async def validator_node(state: OrchestratorState) -> dict[str, Any]:
        errors: list[str] = []
        if state.get("failed_subtasks"):
            errors.append("one or more subtasks exhausted their retry budget")
        if not state.get("subtask_results"):
            errors.append("no subtask produced a result")
        for raw in state.get("subtask_results", []):
            try:
                result = SubTaskResult.model_validate(raw)
                if not result.output.strip() or result.confidence <= 0:
                    errors.append(f"invalid result from {result.subtask_id}")
            except Exception as exc:
                errors.append(f"invalid subtask result: {exc}")
        return {"status": TaskStatus.VALIDATING, "validation_errors": errors}

    async def synthesizer_node(state: OrchestratorState) -> dict[str, Any]:
        results = [SubTaskResult.model_validate(item) for item in state["subtask_results"]]
        weights = [max(result.token_count, 1) for result in results]
        confidence = sum(
            result.confidence * weight for result, weight in zip(results, weights, strict=True)
        ) / sum(weights)
        sources = list(dict.fromkeys(source for result in results for source in result.sources))
        task_result = TaskResult(
            output="\n\n".join(result.output for result in results),
            confidence=confidence,
            subtask_results=results,
            sources=sources,
            total_tokens=sum(result.token_count for result in results),
            total_cost_usd=sum(result.cost_usd for result in results),
        )
        return {
            "status": TaskStatus.COMPLETED,
            "result": task_result.model_dump(mode="json"),
            "total_tokens": task_result.total_tokens,
            "total_cost_usd": task_result.total_cost_usd,
        }

    async def error_handler_node(state: OrchestratorState) -> dict[str, Any]:
        error = (
            "; ".join(state.get("validation_errors", []))
            or state.get("error")
            or "orchestration failed"
        )
        return {"status": TaskStatus.FAILED, "error": error}

    def after_dispatch(state: OrchestratorState) -> str:
        return "error" if state.get("failed_subtasks") else "validator"

    def after_validation(state: OrchestratorState) -> str:
        return "error" if state.get("validation_errors") else "synthesizer"

    graph = StateGraph(OrchestratorState)
    graph.add_node("planner", planner.plan_task)
    graph.add_node("dispatcher", dispatcher.dispatch_subtasks)
    graph.add_node("validator", validator_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "dispatcher")
    graph.add_conditional_edges(
        "dispatcher", after_dispatch, {"validator": "validator", "error": "error_handler"}
    )
    graph.add_conditional_edges(
        "validator", after_validation, {"synthesizer": "synthesizer", "error": "error_handler"}
    )
    graph.add_edge("synthesizer", END)
    graph.add_edge("error_handler", END)
    return graph.compile()


class OrchestratorEngine:
    """Public async API for running a user task through the orchestration pipeline."""

    def __init__(
        self, *, planner: PlannerNode | None = None, dispatcher: DispatcherNode | None = None
    ) -> None:
        self.planner = planner or PlannerNode()
        self.dispatcher = dispatcher or DispatcherNode()

    @cached_property
    def graph(self) -> Any:
        return build_orchestrator_graph(self.planner, self.dispatcher)

    async def run_task(
        self, task_create: TaskCreate, *, task_id: str | None = None
    ) -> TaskResponse:
        state = create_orchestrator_state(
            task_description=task_create.description,
            task_id=task_id,
            priority=int(task_create.priority),
        )
        await self._create_task_record(state, task_create)
        started = datetime.now(UTC)
        try:
            final_state = await asyncio.wait_for(
                self.graph.ainvoke(state), timeout=get_settings().ORCHESTRATOR_TIMEOUT
            )
        except TimeoutError:
            final_state = {**state, "status": TaskStatus.TIMED_OUT, "error": "orchestrator timeout"}
        except Exception as exc:
            final_state = {**state, "status": TaskStatus.FAILED, "error": str(exc)}
        await self._update_task_record(final_state, started)
        result = (
            TaskResult.model_validate(final_state["result"]) if final_state.get("result") else None
        )
        return TaskResponse(
            task_id=final_state["task_id"],
            description=task_create.description,
            priority=task_create.priority,
            status=TaskStatus(final_state["status"]),
            result=result,
            error=final_state.get("error"),
            completed_at=datetime.now(UTC)
            if TaskStatus(final_state["status"]).is_terminal
            else None,
        )

    async def _create_task_record(self, state: OrchestratorState, task: TaskCreate) -> None:
        try:
            from src.db.session import get_managed_session

            async with get_managed_session() as session:
                session.add(
                    TaskRecord(
                        id=UUID(state["task_id"]),
                        description=task.description,
                        priority=int(task.priority),
                        status=TaskStatus.PENDING.value,
                        metadata_=task.metadata,
                    )
                )
        except RuntimeError:
            return

    async def _update_task_record(self, state: OrchestratorState, started: datetime) -> None:
        try:
            from src.db.session import get_managed_session

            async with get_managed_session() as session:
                record = await session.get(TaskRecord, UUID(state["task_id"]))
                if record:
                    record.status = TaskStatus(state["status"]).value
                    record.result = state.get("result")
                    record.error = state.get("error")
                    record.total_tokens = state.get("total_tokens", 0)
                    record.total_cost_usd = state.get("total_cost_usd", 0.0)
                    record.duration_seconds = (datetime.now(UTC) - started).total_seconds()
                    record.completed_at = datetime.now(UTC)
        except RuntimeError:
            return
