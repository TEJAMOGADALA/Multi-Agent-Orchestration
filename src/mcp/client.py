"""Adapt remote MCP capabilities to the local :class:`BaseTool` contract."""

from __future__ import annotations

import re
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, create_model, model_validator

from src.config.constants import MCP_MAX_TOOLS_PER_SERVER, AgentType, MCPToolSource, MCPTransport
from src.config.settings import get_settings
from src.tools.base import BaseTool, ToolRegistry, ToolResult

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from mcp.client.session import ClientSession


class MCPServerConfig(BaseModel):
    """A deliberately explicit external-server configuration."""

    name: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    transport: MCPTransport
    url: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_transport_details(self) -> MCPServerConfig:
        if self.transport is MCPTransport.STDIO and not self.command:
            raise ValueError("stdio servers require a command")
        if self.transport is not MCPTransport.STDIO and not self.url:
            raise ValueError("HTTP MCP servers require a URL")
        return self


def _schema_type(schema: dict[str, Any]) -> type[Any]:
    type_name = str(schema.get("type", ""))
    type_map: dict[str, type[Any]] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(type_name, Any)


def _args_schema(name: str, schema: dict[str, Any] | None) -> type[BaseModel]:
    schema = schema or {}
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for key, value in schema.get("properties", {}).items():
        fields[key] = (_schema_type(value), ... if key in required else None)
    model_name = (
        "MCP" + "".join(part.capitalize() for part in name.replace("-", "_").split("_")) + "Args"
    )
    from typing import cast

    return cast("type[BaseModel]", create_model(model_name, **fields))


class MCPTool(BaseTool):
    """One discoverable remote MCP capability exposed as a local async tool."""

    source: MCPToolSource = MCPToolSource.MCP
    supported_agents: frozenset[AgentType] = frozenset()

    def __init__(self, hub: MCPClientHub, server: MCPServerConfig, tool: Any) -> None:
        self._hub = hub
        self._server = server
        self._remote_name = tool.name
        self.name = re.sub(r"\W", "_", f"mcp_{server.name}_{tool.name}")
        self.description = tool.description or f"MCP tool {tool.name} from {server.name}"
        self.args_schema = _args_schema(self.name, getattr(tool, "input_schema", None))

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self._hub.call_tool(self._server, self._remote_name, kwargs)


class MCPClientHub:
    """Short-lived MCP sessions avoid leaked subprocesses and stale HTTP connections."""

    @asynccontextmanager
    async def _session(self, server: MCPServerConfig) -> AsyncIterator[ClientSession]:
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.streamable_http import streamable_http_client
        from mcp.shared._httpx_utils import create_mcp_http_client

        timeout = get_settings().MCP_CLIENT_TIMEOUT
        if server.transport is MCPTransport.STDIO:
            transport = stdio_client(
                StdioServerParameters(
                    command=server.command or "", args=server.args, env=server.env or None
                )
            )
        elif server.transport is MCPTransport.SSE:
            transport = sse_client(
                server.url or "", headers=server.headers or None, timeout=float(timeout)
            )
        else:
            http_client = create_mcp_http_client(headers=server.headers or None)
            transport = streamable_http_client(server.url or "", http_client=http_client)
        async with AsyncExitStack() as stack:
            if server.transport is MCPTransport.STREAMABLE_HTTP:
                await stack.enter_async_context(http_client)
            read_stream, write_stream = await stack.enter_async_context(transport)
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream, read_timeout_seconds=timeout)
            )
            await session.initialize()
            yield session

    async def discover(
        self, server: MCPServerConfig, registry: ToolRegistry | None = None
    ) -> list[MCPTool]:
        """List, adapt, and register at most the configured safe number of tools."""
        if not get_settings().MCP_DISCOVERY_ENABLED:
            return []
        registry = registry or ToolRegistry.instance()
        discovered: list[MCPTool] = []
        async with self._session(server) as session:
            listing = await session.list_tools()
        for remote_tool in listing.tools[:MCP_MAX_TOOLS_PER_SERVER]:
            tool = MCPTool(self, server, remote_tool)
            if registry.get(tool.name) is None:
                registry.register(tool)
                discovered.append(tool)
        return discovered

    async def call_tool(
        self, server: MCPServerConfig, name: str, arguments: dict[str, Any]
    ) -> ToolResult:
        try:
            async with self._session(server) as session:
                result = await session.call_tool(name, arguments)
            payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            is_error = bool(getattr(result, "is_error", False))
            return ToolResult(
                result=payload,
                is_error=is_error,
                error="MCP tool returned an error" if is_error else None,
            )
        except Exception as exc:
            return ToolResult(
                error=f"MCP call to {server.name}/{name} failed: {exc}", is_error=True
            )
