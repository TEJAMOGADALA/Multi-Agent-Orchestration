"""Constrained data-access tools for the Analysis agent."""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.config.constants import AgentType
from src.db.session import get_managed_session
from src.tools.base import BaseTool, ToolResult
from src.tools.network import validate_public_url


class DatabaseQueryArgs(BaseModel):
    query: str = Field(min_length=8, max_length=10_000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    max_rows: int = Field(default=100, ge=1, le=1_000)


class ApiCallArgs(BaseModel):
    url: str = Field(min_length=10, max_length=2_000)
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DatabaseQueryTool(BaseTool):
    name: ClassVar[str] = "database_query"
    description: ClassVar[str] = "Run a parameterized, read-only SQL query against DevAgent data."
    args_schema: ClassVar[type[BaseModel]] = DatabaseQueryArgs
    supported_agents: ClassVar[set[AgentType]] = {AgentType.ANALYSIS}

    async def execute(
        self, *, query: str, parameters: dict[str, Any] | None = None, max_rows: int = 100
    ) -> ToolResult:
        normalized = query.strip().lower()
        if ";" in normalized or not normalized.startswith(("select", "with", "explain")):
            return ToolResult(
                error="only one read-only SELECT, WITH, or EXPLAIN query is allowed", is_error=True
            )
        forbidden_operations = {
            "insert",
            "update",
            "delete",
            "alter",
            "drop",
            "create",
            "grant",
            "revoke",
            "copy",
            "call",
            "do",
            "execute",
            "merge",
            "truncate",
        }
        forbidden = rf"\b({'|'.join(forbidden_operations)})\b"
        if re.search(forbidden, normalized):
            return ToolResult(
                error="query contains a write or administrative operation", is_error=True
            )
        async with get_managed_session() as session:
            result = await session.execute(text(query), parameters or {})
            rows = [dict(row) for row in result.mappings().fetchmany(max_rows)]
        return ToolResult(
            result={"rows": json.loads(json.dumps(rows, default=str)), "row_count": len(rows)}
        )


class ApiCallerTool(BaseTool):
    name: ClassVar[str] = "api_caller"
    description: ClassVar[str] = "Perform a safe, bounded GET request to a public API."
    args_schema: ClassVar[type[BaseModel]] = ApiCallArgs
    supported_agents: ClassVar[set[AgentType]] = {AgentType.ANALYSIS}

    async def execute(
        self, *, url: str, params: dict[str, str | int | float | bool] | None = None
    ) -> ToolResult:
        target = await validate_public_url(url)
        async with (
            httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client,
            client.stream("GET", target, params=params) as response,
        ):
            response.raise_for_status()
            content_length = int(response.headers.get("content-length", 0) or 0)
            if content_length > 1_000_000:
                return ToolResult(error="response exceeds the 1 MB limit", is_error=True)
            chunks: list[bytes] = []
            received = 0
            async for chunk in response.aiter_bytes():
                received += len(chunk)
                if received > 1_000_000:
                    return ToolResult(error="response exceeds the 1 MB limit", is_error=True)
                chunks.append(chunk)
            body = b"".join(chunks)
        try:
            content: Any = json.loads(body)
        except json.JSONDecodeError:
            content = body.decode("utf-8", errors="replace")
        return ToolResult(
            result={
                "url": str(response.url),
                "status_code": response.status_code,
                "content": content,
            }
        )
