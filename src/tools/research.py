"""Source-oriented research tools with bounded external content handling."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, Field, HttpUrl

from src.config.constants import AgentType
from src.config.settings import get_settings
from src.tools.base import BaseTool, ToolResult
from src.tools.network import validate_public_url

_MAX_RESPONSE_BYTES = 1_000_000


class WebSearchArgs(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)


class WebFetchArgs(BaseModel):
    url: HttpUrl


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the public web and return concise, source-attributed results."
    args_schema: type[BaseModel] | None = WebSearchArgs
    supported_agents: frozenset[AgentType] = frozenset({AgentType.RESEARCH})

    async def execute(  # type: ignore[override]
        self, *, query: str, max_results: int = 5
    ) -> ToolResult:
        api_key = get_settings().TAVILY_API_KEY.get_secret_value()
        if not api_key:
            return ToolResult(error="TAVILY_API_KEY is not configured", is_error=True)
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
        data = response.json()
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:2000],
                "score": item.get("score"),
            }
            for item in data.get("results", [])[:max_results]
        ]
        return ToolResult(result={"answer": data.get("answer"), "results": results})


class WebFetchTool(BaseTool):
    name: str = "web_fetch"
    description: str = "Fetch bounded textual content from a public URL for research."
    args_schema: type[BaseModel] | None = WebFetchArgs
    supported_agents: frozenset[AgentType] = frozenset({AgentType.RESEARCH})

    async def execute(self, *, url: HttpUrl | str) -> ToolResult:  # type: ignore[override]
        target = await validate_public_url(str(url))
        async with (
            httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client,
            client.stream(
                "GET", target, headers={"Accept": "text/plain,text/html,application/json"}
            ) as response,
        ):
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)
                size += len(chunk)
                if size > _MAX_RESPONSE_BYTES:
                    break
        text = b"".join(chunks).decode("utf-8", errors="replace")
        return ToolResult(
            result={
                "url": target,
                "content": text[:4000],
                "truncated": size > _MAX_RESPONSE_BYTES or len(text) > 4000,
                "bytes_read": size,
            }
        )
