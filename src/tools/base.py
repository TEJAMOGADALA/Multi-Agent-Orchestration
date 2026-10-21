"""Small provider-agnostic tool abstraction with a LangChain adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import RLock
from time import perf_counter
from typing import TYPE_CHECKING, Any, ClassVar

from src.config.constants import AgentType, MCPToolSource

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass(slots=True)
class ToolResult:
    result: Any = None
    error: str | None = None
    is_error: bool = False
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    args_schema: ClassVar[type[BaseModel] | None] = None
    supported_agents: ClassVar[set[AgentType]] = set()
    source: ClassVar[MCPToolSource] = MCPToolSource.INTERNAL

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute this tool and return a serializable result."""


class ToolRegistry:
    _instance: ClassVar[ToolRegistry | None] = None
    _lock: ClassVar[RLock] = RLock()

    def __new__(cls) -> ToolRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_tools"):
            return
        self._tools: dict[str, BaseTool] = {}

    @classmethod
    def instance(cls) -> ToolRegistry:
        return cls()

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("tool name is required")
        with self._lock:
            if tool.name in self._tools:
                raise ValueError(f"tool already registered: {tool.name}")
            self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_tools_for_agent(self, agent_type: AgentType) -> list[BaseTool]:
        return [
            tool
            for tool in self._tools.values()
            if not tool.supported_agents or agent_type in tool.supported_agents
        ]


async def _run_tool(tool: BaseTool, **kwargs: Any) -> dict[str, Any]:
    started = perf_counter()
    try:
        outcome = await tool.execute(**kwargs)
        outcome.duration_seconds = outcome.duration_seconds or perf_counter() - started
        return {
            "result": outcome.result,
            "error": outcome.error,
            "is_error": outcome.is_error,
            "metadata": outcome.metadata,
            "duration_seconds": outcome.duration_seconds,
        }
    except Exception as exc:
        return {
            "result": None,
            "error": str(exc),
            "is_error": True,
            "metadata": {},
            "duration_seconds": perf_counter() - started,
        }


def tool_to_langchain(base_tool: BaseTool) -> Any:
    from langchain_core.tools import StructuredTool

    async def invoke(**kwargs: Any) -> dict[str, Any]:
        return await _run_tool(base_tool, **kwargs)

    return StructuredTool.from_function(
        coroutine=invoke,
        name=base_tool.name,
        description=base_tool.description,
        args_schema=base_tool.args_schema,
    )
