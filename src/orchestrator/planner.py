"""LLM-backed task decomposition with strict DAG validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config.constants import ORCHESTRATOR_SYSTEM_PROMPT, AgentType, SubTaskStatus, TaskStatus
from src.config.settings import get_settings
from src.llm.factory import get_llm_with_fallback
from src.models.database import SubTaskRecord

if TYPE_CHECKING:
    from src.models.state import OrchestratorState


class PlannedSubtask(BaseModel):
    description: str = Field(min_length=1)
    agent_type: AgentType
    order: int = Field(ge=0)
    dependencies: list[int] = Field(
        default_factory=list, description="Indexes of prerequisite subtasks"
    )
    tools_required: list[str] = Field(default_factory=list)


class PlanSchema(BaseModel):
    subtasks: list[PlannedSubtask] = Field(min_length=1)
    reasoning: str = ""


class PlannerNode:
    def __init__(self, *, llm: Any | None = None, max_subtasks: int | None = None) -> None:
        self.llm = llm or get_llm_with_fallback()
        self.max_subtasks = max_subtasks or get_settings().ORCHESTRATOR_MAX_SUBTASKS

    @staticmethod
    def _validate_dag(plan: list[dict[str, Any]]) -> None:
        ids = {item["subtask_id"] for item in plan}
        graph = {item["subtask_id"]: set(item["dependencies"]) for item in plan}
        if any(not deps <= ids for deps in graph.values()):
            raise ValueError("plan has unknown dependency references")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("plan contains a circular dependency")
            if node not in visited:
                visiting.add(node)
                for dependency in graph[node]:
                    visit(dependency)
                visiting.remove(node)
                visited.add(node)

        for node in graph:
            visit(node)

    async def plan_task(self, state: OrchestratorState) -> dict[str, Any]:
        prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(max_subtasks=self.max_subtasks)
        prompt += (
            "\nReturn only a plan. dependencies must contain zero-based indexes of earlier "
            "subtasks, never self-references.\n\nUser task:\n" + state["task_description"]
        )
        structured_llm = self.llm.with_structured_output(PlanSchema)
        response = await structured_llm.ainvoke(prompt)
        parsed = (
            response if isinstance(response, PlanSchema) else PlanSchema.model_validate(response)
        )
        if len(parsed.subtasks) > self.max_subtasks:
            raise ValueError(f"plan exceeds the {self.max_subtasks}-subtask limit")

        ids = [str(uuid4()) for _ in parsed.subtasks]
        plan: list[dict[str, Any]] = []
        for index, item in enumerate(parsed.subtasks):
            if any(dependency < 0 or dependency >= index for dependency in item.dependencies):
                raise ValueError("each dependency must reference an earlier subtask")
            plan.append(
                {
                    "subtask_id": ids[index],
                    "description": item.description,
                    "agent_type": item.agent_type.value,
                    "order": item.order,
                    "dependencies": [ids[dependency] for dependency in item.dependencies],
                    "tools_required": item.tools_required,
                }
            )
        self._validate_dag(plan)
        subtask_states = {
            item["subtask_id"]: {"status": SubTaskStatus.PENDING.value, "retry_count": 0, **item}
            for item in plan
        }
        await self._persist_plan(state["task_id"], plan)
        return {
            "status": TaskStatus.EXECUTING,
            "plan": plan,
            "subtask_states": subtask_states,
            "pending_subtasks": ids,
            "planning_reasoning": parsed.reasoning,
        }

    async def _persist_plan(self, task_id: str, plan: list[dict[str, Any]]) -> None:
        """Persist when the database lifecycle has been started; stay usable without it."""
        try:
            from src.db.session import get_managed_session

            task_uuid = UUID(task_id)
            async with get_managed_session() as session:
                for item in plan:
                    session.add(
                        SubTaskRecord(
                            id=item["subtask_id"],
                            task_id=task_uuid,
                            description=item["description"],
                            agent_type=item["agent_type"],
                            order=item["order"],
                            dependencies=item["dependencies"],
                        )
                    )
        except RuntimeError:
            return
