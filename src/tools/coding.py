"""Narrow, sandboxed coding tools for the Coding agent."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, field_validator

from src.config.constants import AgentType
from src.config.settings import get_settings
from src.tools.base import BaseTool, ToolResult


class CodeExecutionArgs(BaseModel):
    code: str = Field(min_length=1, max_length=30_000)
    language: Literal["python"] = "python"
    stdin: str = Field(default="", max_length=10_000)


class GitHubArgs(BaseModel):
    action: Literal["get_file", "search_code", "list_issues"]
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    path: str | None = Field(default=None, max_length=500)
    query: str | None = Field(default=None, max_length=500)

    @field_validator("path")
    @classmethod
    def reject_path_traversal(cls, value: str | None) -> str | None:
        if value and (".." in value.split("/") or value.startswith("/")):
            raise ValueError("path traversal is not allowed")
        return value


class CodeExecutorTool(BaseTool):
    name: ClassVar[str] = "code_executor"
    description: ClassVar[str] = "Execute Python in an isolated, network-disabled Docker container."
    args_schema: ClassVar[type[BaseModel]] = CodeExecutionArgs
    supported_agents: ClassVar[set[AgentType]] = {AgentType.CODING}

    async def execute(self, *, code: str, language: str = "python", stdin: str = "") -> ToolResult:
        if language != "python":
            return ToolResult(error="only Python execution is available", is_error=True)
        settings = get_settings()
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            f"{settings.CODE_EXECUTOR_MAX_MEMORY_MB}m",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",  # noqa: S108 - isolated container scratch space.
            settings.CODE_EXECUTOR_DOCKER_IMAGE,
            "python",
            "-I",
            "-c",
            code,
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return ToolResult(error="Docker is required for code execution", is_error=True)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin.encode()), settings.CODE_EXECUTOR_TIMEOUT
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return ToolResult(error="code execution timed out", is_error=True)
        return ToolResult(
            result={
                "exit_code": process.returncode,
                "stdout": stdout.decode(errors="replace")[:20_000],
                "stderr": stderr.decode(errors="replace")[:20_000],
            },
            is_error=process.returncode != 0,
        )


class GitHubTool(BaseTool):
    name: ClassVar[str] = "github"
    description: ClassVar[str] = (
        "Read repository files, search code, or list issues through the GitHub API."
    )
    args_schema: ClassVar[type[BaseModel]] = GitHubArgs
    supported_agents: ClassVar[set[AgentType]] = {AgentType.CODING}

    async def execute(
        self, *, action: str, repository: str, path: str | None = None, query: str | None = None
    ) -> ToolResult:
        token = get_settings().GITHUB_TOKEN.get_secret_value()
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if action == "get_file":
            if not path:
                return ToolResult(error="path is required for get_file", is_error=True)
            endpoint = f"/repos/{repository}/contents/{quote(path, safe='/')}"
        elif action == "search_code":
            if not query:
                return ToolResult(error="query is required for search_code", is_error=True)
            endpoint = "/search/code"
        else:
            endpoint = f"/repos/{repository}/issues?state=open&per_page=30"
        async with httpx.AsyncClient(
            base_url="https://api.github.com", headers=headers, timeout=20.0
        ) as client:
            response = await client.get(
                endpoint,
                params={"q": f"{query} repo:{repository}"} if action == "search_code" else None,
            )
            response.raise_for_status()
        payload: Any = response.json()
        return ToolResult(result=payload)
