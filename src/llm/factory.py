"""Lazy multi-provider LangChain chat-model factory."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

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
    common: dict[str, Any] = {
        "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature
    }
    common.update(kwargs)
    timeout = common.pop("timeout", settings.LLM_REQUEST_TIMEOUT)
    api_key = common.pop("api_key", None)
    secret_key: SecretStr | None = (
        SecretStr(api_key)
        if isinstance(api_key, str)
        else (api_key if isinstance(api_key, SecretStr) else None)
    )
    token_limit = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    if provider is LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=model,
            api_key=secret_key or settings.OPENAI_API_KEY,
            timeout=timeout,
            max_tokens=token_limit,
            organization=settings.OPENAI_ORG_ID or None,
            **common,
        )
    if provider is LLMProvider.AZURE_OPENAI:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(  # type: ignore[call-arg]
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT or model,
            model=model,
            api_key=secret_key or settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=timeout,
            max_tokens=token_limit,
            **common,
        )
    if provider is LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # type: ignore[call-arg]
            model=model,
            api_key=secret_key or settings.ANTHROPIC_API_KEY,
            timeout=timeout,
            max_tokens=token_limit,
            **common,
        )
    if provider is LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=secret_key or settings.GOOGLE_API_KEY,
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
    return create_chat_model(
        settings.LLM_FALLBACK_PROVIDER,
        settings.LLM_FALLBACK_MODEL,
        **kwargs,
    )


def get_llm_with_fallback(**kwargs: Any) -> Any:
    """Return a model which falls back transparently on transient API failures."""
    primary = get_primary_llm(**kwargs)
    fallback = get_fallback_llm(**kwargs)
    if fallback is None:
        return primary
    return primary.with_fallbacks([fallback])


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate the estimated USD cost of an LLM call from cached pricing tiers."""
    pricing = LLM_COST_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        for known_model, tier in LLM_COST_PER_MILLION_TOKENS.items():
            if model.startswith(known_model) or known_model.startswith(model):
                pricing = tier
                break
    if pricing is None:
        return 0.0
    input_cost = (prompt_tokens / 1_000_000.0) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)


def estimate_token_count(text: str, model: str = "gpt-4o-mini") -> int:
    """High-speed local token estimator using tiktoken with conservative fallback."""
    if not text:
        return 0
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4)
