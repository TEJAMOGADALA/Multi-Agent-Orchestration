"""Registration point for the small built-in Phase 4 tool set."""

from __future__ import annotations

from src.tools.analysis import ApiCallerTool, DatabaseQueryTool
from src.tools.base import ToolRegistry
from src.tools.coding import CodeExecutorTool, GitHubTool
from src.tools.research import WebFetchTool, WebSearchTool


def register_default_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    registry = registry or ToolRegistry.instance()
    for tool_type in (
        WebSearchTool,
        WebFetchTool,
        CodeExecutorTool,
        GitHubTool,
        DatabaseQueryTool,
        ApiCallerTool,
    ):
        if registry.get(tool_type.name) is None:
            registry.register(tool_type())
    return registry
