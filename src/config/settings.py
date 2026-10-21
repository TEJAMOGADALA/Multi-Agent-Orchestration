# ============================================================
# DevAgent — Multi-Agent Orchestration System
# src/config/settings.py — Pydantic Settings (env var validation)
# ============================================================
# This module is the SINGLE SOURCE OF TRUTH for all configuration.
# It reads from .env, validates types, enforces constraints, and
# provides sensible defaults. Every other module imports settings
# from here — never reads os.environ directly.
#
# Usage:
#   from src.config.settings import get_settings
#   settings = get_settings()  # Cached singleton
#   print(settings.APP_NAME)   # "DevAgent"
#   print(settings.LLM_MODEL)  # "gemini-1.5-flash"
# ============================================================

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ----------------------------------------------------------
# Project root — used to locate .env file
# ----------------------------------------------------------
# Resolves to: Multi-Agent-Orchestration/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    Settings are grouped by subsystem. Each group can be independently
    disabled via feature flags (e.g., SLACK_ENABLED=false) so the app
    doesn't crash when optional services aren't configured yet.
    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        # Load from .env file at project root
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        # Don't fail if .env is missing (use defaults / actual env vars)
        env_ignore_empty=True,
        # Allow extra fields without raising validation errors
        extra="ignore",
        # Case-sensitive env var names
        case_sensitive=True,
    )

    # ==========================================================
    # 1. APPLICATION
    # ==========================================================
    APP_NAME: str = "DevAgent"
    APP_ENV: str = Field(
        default="development",
        pattern=r"^(development|staging|production)$",
        description="Application environment",
    )
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    APP_LOG_LEVEL: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    APP_SECRET_KEY: SecretStr = Field(
        default=SecretStr("CHANGE_ME_generate_a_secure_random_key"),
        description="Secret key for JWT signing. MUST be changed in production.",
    )
    APP_API_KEYS: str = Field(
        default="dev-key-change-me-1",
        description="Comma-separated list of valid API keys",
    )

    # ==========================================================
    # 2. LLM PROVIDERS
    # ==========================================================
    LLM_PROVIDER: str = Field(
        default="google",
        pattern=r"^(openai|azure_openai|anthropic|google)$",
        description="Primary LLM provider",
    )
    LLM_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Model identifier for the selected provider",
    )
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=4096, ge=1, le=128000)
    LLM_REQUEST_TIMEOUT: int = Field(default=60, ge=5, le=300)

    # Provider API keys (SecretStr hides values in logs/repr)
    OPENAI_API_KEY: SecretStr = SecretStr("")
    OPENAI_ORG_ID: str = ""
    AZURE_OPENAI_API_KEY: SecretStr = SecretStr("")
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"
    AZURE_OPENAI_DEPLOYMENT: str = ""
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    GOOGLE_API_KEY: SecretStr = SecretStr("")
    GOOGLE_PROJECT_ID: str = ""

    # Fallback LLM
    LLM_FALLBACK_PROVIDER: str = ""
    LLM_FALLBACK_MODEL: str = ""
    LLM_FALLBACK_API_KEY: SecretStr = SecretStr("")

    # ==========================================================
    # 3. POSTGRESQL
    # ==========================================================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = "devagent"
    POSTGRES_USER: str = "devagent"
    POSTGRES_PASSWORD: SecretStr = SecretStr("CHANGE_ME_strong_db_password")
    DATABASE_URL: str = ""
    POSTGRES_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    POSTGRES_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    POSTGRES_POOL_TIMEOUT: int = Field(default=30, ge=5, le=120)

    # ==========================================================
    # 4. REDIS
    # ==========================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_PASSWORD: SecretStr = SecretStr("")
    REDIS_DB: int = Field(default=0, ge=0, le=15)
    REDIS_SSL: bool = False
    REDIS_URL: str = ""
    REDIS_DEFAULT_TTL: int = Field(default=3600, ge=60)
    REDIS_SESSION_TTL: int = Field(default=86400, ge=3600)

    # ==========================================================
    # 5. PINECONE
    # ==========================================================
    PINECONE_API_KEY: SecretStr = SecretStr("")
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "devagent-knowledge"
    PINECONE_DIMENSION: int = Field(default=1536, ge=1)
    PINECONE_METRIC: str = Field(
        default="cosine",
        pattern=r"^(cosine|euclidean|dotproduct)$",
    )
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ==========================================================
    # 6. TOOLS
    # ==========================================================
    TAVILY_API_KEY: SecretStr = SecretStr("")
    SERPAPI_API_KEY: SecretStr = SecretStr("")
    GITHUB_TOKEN: SecretStr = SecretStr("")
    GITHUB_DEFAULT_ORG: str = ""
    CODE_EXECUTOR_TIMEOUT: int = Field(default=30, ge=5, le=120)
    CODE_EXECUTOR_MAX_MEMORY_MB: int = Field(default=256, ge=64, le=2048)
    CODE_EXECUTOR_DOCKER_IMAGE: str = "python:3.12-slim"

    # ==========================================================
    # 7. MCP (Model Context Protocol)
    # ==========================================================
    MCP_DISCOVERY_ENABLED: bool = True
    MCP_CLIENT_TIMEOUT: int = Field(default=30, ge=5, le=120)
    MCP_MAX_RETRIES: int = Field(default=3, ge=0, le=10)
    MCP_CACHE_TTL: int = Field(default=300, ge=60)
    MCP_AUTH_TOKEN_CHROME_DEVTOOLS: SecretStr = SecretStr("")
    MCP_AUTH_TOKEN_MONGODB: SecretStr = SecretStr("")
    MCP_AUTH_TOKEN_CUSTOM: SecretStr = SecretStr("")
    MCP_SERVER_ENABLED: bool = False
    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = Field(default=8001, ge=1, le=65535)
    MCP_SERVER_AUTH_TOKEN: SecretStr = SecretStr("")

    # ==========================================================
    # 8. MONITORING & OBSERVABILITY
    # ==========================================================
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "devagent"
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = Field(default=1.0, ge=0.0, le=1.0)
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = Field(default=9090, ge=1, le=65535)
    COST_TRACKING_ENABLED: bool = True
    COST_ALERT_THRESHOLD_USD: float = Field(default=50.0, ge=0.0)

    # ==========================================================
    # 9. EXTERNAL INTEGRATIONS
    # ==========================================================
    SLACK_WEBHOOK_URL: str = ""
    SLACK_CHANNEL: str = "#devagent-alerts"
    SLACK_ENABLED: bool = False
    NOTION_API_KEY: SecretStr = SecretStr("")
    NOTION_DATABASE_ID: str = ""
    NOTION_ENABLED: bool = False
    GITHUB_WEBHOOK_SECRET: SecretStr = SecretStr("")

    # ==========================================================
    # 10. RATE LIMITING & SECURITY
    # ==========================================================
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1)
    LLM_RATE_LIMIT_RPM: int = Field(default=60, ge=1)
    LLM_RATE_LIMIT_TPM: int = Field(default=100000, ge=1)
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    MAX_REQUEST_SIZE_MB: int = Field(default=10, ge=1, le=100)
    MAX_TASK_DESCRIPTION_LENGTH: int = Field(default=10000, ge=100)

    # ==========================================================
    # 11. AGENT CONFIGURATION
    # ==========================================================
    ORCHESTRATOR_MAX_SUBTASKS: int = Field(default=10, ge=1, le=50)
    AGENT_MAX_RETRIES: int = Field(default=3, ge=0, le=10)
    ORCHESTRATOR_TIMEOUT: int = Field(default=300, ge=30, le=1800)
    AGENT_MAX_CONCURRENCY: int = Field(default=5, ge=1, le=20)

    # ==========================================================
    # COMPUTED PROPERTIES
    # ==========================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"

    @property
    def api_keys_list(self) -> list[str]:
        """Parse comma-separated API keys into a list."""
        return [key.strip() for key in self.APP_API_KEYS.split(",") if key.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url_computed(self) -> str:
        """
        Return DATABASE_URL if explicitly set, otherwise construct from
        individual POSTGRES_* variables.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url_computed(self) -> str:
        """
        Return REDIS_URL if explicitly set, otherwise construct from
        individual REDIS_* variables.
        """
        if self.REDIS_URL:
            return self.REDIS_URL
        password = self.REDIS_PASSWORD.get_secret_value()
        scheme = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{password}@" if password else ""
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==========================================================
    # VALIDATORS
    # ==========================================================

    @field_validator("APP_LOG_LEVEL", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        """Ensure log level is uppercase."""
        return v.upper().strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_llm_provider_keys(self) -> "Settings":
        """
        Ensure the selected LLM provider has its API key configured.
        This prevents runtime failures when an agent tries to call the LLM.
        """
        provider = self.LLM_PROVIDER
        key_map: dict[str, SecretStr] = {
            "openai": self.OPENAI_API_KEY,
            "azure_openai": self.AZURE_OPENAI_API_KEY,
            "anthropic": self.ANTHROPIC_API_KEY,
            "google": self.GOOGLE_API_KEY,
        }

        api_key = key_map.get(provider)
        if api_key and not api_key.get_secret_value():
            raise ValueError(
                f"LLM_PROVIDER is set to '{provider}' but its API key is empty. "
                f"Please set the corresponding API key in your .env file."
            )

        # Azure-specific validation
        if provider == "azure_openai":
            if not self.AZURE_OPENAI_ENDPOINT:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT is required when LLM_PROVIDER=azure_openai"
                )
            if not self.AZURE_OPENAI_DEPLOYMENT:
                raise ValueError(
                    "AZURE_OPENAI_DEPLOYMENT is required when LLM_PROVIDER=azure_openai"
                )

        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """
        Enforce stricter validation in production:
        - Secret key must be changed from default
        - Debug must be disabled
        - OTEL trace sampling should be reduced
        """
        if self.APP_ENV == "production":
            # Check secret key is not the default placeholder
            if "CHANGE_ME" in self.APP_SECRET_KEY.get_secret_value():
                raise ValueError(
                    "APP_SECRET_KEY must be changed from default in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )

            # Warn about debug mode in production (don't crash, just log)
            if self.APP_DEBUG:
                import warnings
                warnings.warn(
                    "APP_DEBUG=true in production is not recommended. "
                    "Set APP_DEBUG=false for production deployments.",
                    UserWarning,
                    stacklevel=2,
                )

        return self


# ----------------------------------------------------------
# Singleton accessor — cached after first call
# ----------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance (singleton pattern).

    The first call loads and validates all settings from .env.
    Subsequent calls return the same instance without re-reading .env.

    Usage:
        settings = get_settings()
        print(settings.APP_NAME)  # "DevAgent"
    """
    return Settings()
