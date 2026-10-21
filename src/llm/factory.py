"""Lazy multi-provider LangChain chat-model factory."""

from __future__ import annotations

from typing import Any

from src.config.constants import LLM_COST_PER_MILLION_TOKENS, LLMProvider
from src.config.settings import get_settings


def _provider(value: LLMProvider | str) -> LLMProvider:
    try:
        return value if isinstance(value, LLMProvider) else LLMProvider(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported LLM provider: {value!r}") from exc


def create_chat_model(
    provider: LLMProvider | str,
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> Any:
    """Create a configured LangChain chat model without importing unused SDKs."""
    settings = get_settings()
    provider = _provider(provider)
    common = {"temperature": settings.LLM_TEMPERATURE if temperature is None else temperature}
    common.update(kwargs)
    timeout = common.pop("timeout", settings.LLM_REQUEST_TIMEOUT)
    api_key = common.pop("api_key", None)
    token_limit = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    if provider is LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=api_key or settings.OPENAI_API_KEY.get_secret_value(),
            timeout=timeout,
            max_tokens=token_limit,
            organization=settings.OPENAI_ORG_ID or None,
            **common,
        )
    if provider is LLMProvider.AZURE_OPENAI:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT or model,
            model=model,
            api_key=api_key or settings.AZURE_OPENAI_API_KEY.get_secret_value(),
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=timeout,
            max_tokens=token_limit,
            **common,
        )
    if provider is LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=api_key or settings.ANTHROPIC_API_KEY.get_secret_value(),
            timeout=timeout,
            max_tokens=token_limit,
            **common,
        )
    if provider is LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key or settings.GOOGLE_API_KEY.get_secret_value(),
            timeout=timeout,
            max_output_tokens=token_limit,
            **common,
        )
    raise AssertionError("all providers must be handled")


def get_primary_llm(**kwargs: Any) -> Any:
    settings = get_settings()
    return create_chat_model(settings.LLM_PROVIDER, settings.LLM_MODEL, **kwargs)


def get_fallback_llm(**kwargs: Any) -> Any | None:
    settings = get_settings()
    if not settings.LLM_FALLBACK_PROVIDER or not settings.LLM_FALLBACK_MODEL:
        return None
    api_key = settings.LLM_FALLBACK_API_KEY.get_secret_value()
    return create_chat_model(
        settings.LLM_FALLBACK_PROVIDER,
        settings.LLM_FALLBACK_MODEL,
        api_key=api_key or None,
        **kwargs,
    )


def get_llm_with_fallback(**kwargs: Any) -> Any:
    primary = get_primary_llm(**kwargs)
    fallback = get_fallback_llm(**kwargs)
    return primary.with_fallbacks([fallback]) if fallback is not None else primary


def estimate_token_count(text: str, model: str = "gpt-4o-mini") -> int:
    """Estimate tokens locally, falling back to a conservative character ratio."""
    try:
        import tiktoken

        return len(tiktoken.encoding_for_model(model).encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4) if text else 0


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    rates = LLM_COST_PER_MILLION_TOKENS.get(model)
    if rates is None:
        rates = next(
            (
                value
                for known_model, value in LLM_COST_PER_MILLION_TOKENS.items()
                if model.startswith(known_model)
            ),
            {"input": 0.0, "output": 0.0},
        )
    return (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000
