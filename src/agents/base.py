"""The bounded ReAct subgraph shared by every specialized agent."""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from src.config.constants import AGENT_TOOL_CALL_MAX_PER_TURN, AgentType, SubTaskStatus
from src.llm.callbacks import TokenTrackingCallback
from src.llm.factory import get_llm_with_fallback
from src.models.schemas import SubTaskResult
from src.models.state import AgentState
from src.tools.base import BaseTool, ToolRegistry, tool_to_langchain


class BaseAgent:
    """A role-configured, bounded agent which can reason and invoke registered tools."""

    def __init__(
        self,
        agent_type: AgentType,
        system_prompt: str,
        *,
        llm: Any | None = None,
        tools: list[BaseTool] | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        if tools is None:
            from src.tools.defaults import register_default_tools

            register_default_tools()
            self.tools = ToolRegistry.instance().get_tools_for_agent(agent_type)
        else:
            self.tools = tools
        self.llm = llm or get_llm_with_fallback()
        self._callback = TokenTrackingCallback(getattr(self.llm, "model_name", "unknown"))
        langchain_tools = [tool_to_langchain(tool) for tool in self.tools]
        self._reasoning_llm = self.llm.bind_tools(langchain_tools) if langchain_tools else self.llm
        self._graph: Any | None = None

    def build_agent_graph(self) -> Any:
        if self._graph is None:
            graph = StateGraph(AgentState)
            graph.add_node("reason", self._reason_node)
            graph.add_node("act", self._act_node)
            graph.add_node("finalize", self._finalize_node)
            graph.add_edge(START, "reason")
            graph.add_conditional_edges(
                "reason", self._should_continue, {"act": "act", "finalize": "finalize"}
            )
            graph.add_edge("act", "reason")
            graph.add_edge("finalize", END)
            self._graph = graph.compile()
        return self._graph

    def _build_system_message(self, state: AgentState) -> SystemMessage:
        context = state.get("shared_context") or {}
        detail = state["subtask_description"]
        if context:
            detail += "\n\nRelevant completed-work context:\n" + json.dumps(context, default=str)
        return SystemMessage(content=f"{self.system_prompt}\n\nYour assigned subtask:\n{detail}")

    async def _reason_node(self, state: AgentState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        if not messages:
            messages = [
                self._build_system_message(state),
                HumanMessage(content=state["subtask_description"]),
            ]
        response = await self._reasoning_llm.ainvoke(
            messages, config={"callbacks": [self._callback]}
        )
        tool_calls = list(getattr(response, "tool_calls", None) or [])[
            :AGENT_TOOL_CALL_MAX_PER_TURN
        ]
        answer = str(response.content) if getattr(response, "content", None) else ""
        return {
            "messages": [*messages, response],
            "pending_tool_calls": tool_calls,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "final_answer": answer if not tool_calls else state.get("final_answer", ""),
            "status": SubTaskStatus.IN_PROGRESS,
        }

    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        audit = list(state.get("tool_calls", []))
        for call in state.get("pending_tool_calls", []):
            name = str(call.get("name", ""))
            tool = ToolRegistry.instance().get(name)
            call_id = str(call.get("id", name))
            if tool is None:
                payload = {"error": f"Tool '{name}' is not available", "is_error": True}
            else:
                from src.tools.base import _run_tool

                payload = await _run_tool(tool, **dict(call.get("args") or {}))
            audit.append(
                {"tool_call_id": call_id, "name": name, "args": call.get("args", {}), **payload}
            )
            messages.append(
                ToolMessage(
                    content=json.dumps(payload, default=str), tool_call_id=call_id, name=name
                )
            )
        return {"messages": messages, "tool_calls": audit, "pending_tool_calls": []}

    def _should_continue(self, state: AgentState) -> str:
        if state.get("iteration_count", 0) >= state.get("max_iterations", self.max_iterations):
            return "finalize"
        return "act" if state.get("pending_tool_calls") else "finalize"

    async def _finalize_node(self, state: AgentState) -> dict[str, Any]:
        answer = state.get("final_answer", "").strip()
        error = state.get("error")
        if not answer:
            answer = "Agent stopped before producing a final answer."
            error = error or "No final answer produced"
        usage = self._callback.get_usage_snapshot()
        result = SubTaskResult(
            subtask_id=state["subtask_id"],
            agent_type=self.agent_type,
            output=answer,
            confidence=0.0 if error else 0.7,
            sources=re.findall(r"https?://[^\s)]+", answer),
            token_count=usage["total_tokens"],
            cost_usd=usage["cost_usd"],
            status=SubTaskStatus.FAILED if error else SubTaskStatus.COMPLETED,
            error=error,
        )
        return {
            "result": result.model_dump(mode="json"),
            "token_usage": [usage],
            "status": result.status,
            "error": error,
        }

    async def invoke(self, state: AgentState) -> AgentState:
        """Run the compiled ReAct graph. Agent instances are single-execution objects."""
        self._callback.reset()
        input_state: dict[str, Any] = dict(state)
        input_state.setdefault("max_iterations", self.max_iterations)
        started = perf_counter()
        output = await self.build_agent_graph().ainvoke(input_state)
        result = dict(output.get("result") or {})
        if result:
            result["duration_seconds"] = perf_counter() - started
            output["result"] = result
        return cast("AgentState", output)
