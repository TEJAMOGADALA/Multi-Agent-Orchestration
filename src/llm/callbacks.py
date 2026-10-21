"""LangChain callback for accumulating provider token usage."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler

from src.llm.factory import calculate_cost


class TokenTrackingCallback(AsyncCallbackHandler):
    """Per-execution callback; do not share one instance across concurrent agents."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.reset()

    async def on_llm_end(self, response: Any, **_: Any) -> None:
        output = getattr(response, "llm_output", None) or {}
        usage = output.get("token_usage") or output.get("usage_metadata") or {}
        if not usage and getattr(response, "generations", None):
            message = response.generations[0][0].message
            usage = getattr(message, "usage_metadata", {}) or {}
        prompt = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        completion = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        self.prompt_tokens += prompt
        self.completion_tokens += completion

    def get_usage_snapshot(self) -> dict[str, Any]:
        total = self.prompt_tokens + self.completion_tokens
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": total,
            "cost_usd": calculate_cost(self.model, self.prompt_tokens, self.completion_tokens),
        }

    def reset(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
