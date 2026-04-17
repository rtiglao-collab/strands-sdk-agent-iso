"""Application configuration (environment-driven)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment and optional `.env` file."""

    model_config = SettingsConfigDict(
        env_prefix="ISO_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    knowledge_dir: str = "knowledge"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
