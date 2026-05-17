"""
Centralized application configuration.

All settings are loaded from environment variables via Pydantic Settings.
Never hardcode secrets — use .env files or secret managers in production.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "support-triage-ai"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 4
    frontend_url: str = "http://localhost:5173"

    # ── Database ─────────────────────────────────────────────
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "support_user"
    postgres_password: str = "change_me_in_production"
    postgres_db: str = "support_triage"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ────────────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker(self) -> str:
        if self.celery_broker_url:
            return self.celery_broker_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/1"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_backend(self) -> str:
        if self.celery_result_backend:
            return self.celery_result_backend
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/2"

    # ── JWT ──────────────────────────────────────────────────
    jwt_secret_key: str = "change-this-to-a-long-random-string-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── AI / LLM ─────────────────────────────────────────────
    ai_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 2048
    openai_temperature: float = 0.1
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── Vector Search ────────────────────────────────────────
    vector_dimension: int = 1536
    similarity_threshold: float = 0.75
    max_similar_results: int = 5

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # ── File Uploads ─────────────────────────────────────────
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 10
    allowed_extensions: str = "pdf,png,jpg,jpeg,gif,txt,csv,doc,docx,xlsx"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",")}

    # ── Email ────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@support-triage.ai"

    # ── Slack ────────────────────────────────────────────────
    slack_webhook_url: str = ""
    slack_bot_token: str = ""

    # ── Observability ────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    sentry_dsn: str = ""

    # ── CORS ─────────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.app_env == "development":
            origins.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
            ])
        return origins

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
