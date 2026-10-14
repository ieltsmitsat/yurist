"""Application configuration settings."""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    PROJECT_NAME: str = "Yurist LegalTech AI Bot"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "dev")
        return bool(v)

    # Telegram Bot (valid token format: <digits>:<alphanumeric>)
    BOT_TOKEN: str = Field(default="1234567890:AAG_mock_bot_token_for_tests123456789")
    BOT_USERNAME: str = Field(default="yurist_bot")
    ADMIN_GROUP_ID: int | None = Field(default=None)
    LAWYER_TELEGRAM_ID: int | None = Field(default=None)
    ADMIN_TELEGRAM_IDS: str = Field(default="")  # Comma separated IDs

    # Server & Webhook
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WEBHOOK_URL: str | None = None
    WEBHOOK_SECRET: str = "yurist_webhook_secret_key"

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/yurist_db"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_database_url(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Configuration (Gemini primary, OpenAI fallback)
    GEMINI_API_KEY: str = Field(default="dummy_gemini_key")
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    OPENAI_API_KEY: str = Field(default="dummy_openai_key")
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_FAST_MODEL: str = "gemini-3.5-flash-lite"
    WHISPER_MODEL: str = "gemini-3.5-flash-lite"
    EMBEDDING_MODEL: str = "gemini-embedding-2"

    # Business Rules
    FREE_QUESTIONS_LIMIT: int = 3
    BUSINESS_TAKEOVER_PAUSE_SECONDS: int = 1800  # 30 minutes
    REFERRAL_BONUS_QUESTIONS: int = 1


settings = Settings()
