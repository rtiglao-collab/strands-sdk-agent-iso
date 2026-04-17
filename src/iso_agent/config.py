"""Application configuration (environment-driven)."""

from functools import lru_cache
from typing import Literal

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

    #: ``demo`` = calculator demo agent; ``neuuf`` = ISO coordinator team (Phase 1 stubs).
    #: Environment: ``ISO_AGENT_PRIMARY_MODE`` (see ``env_prefix``).
    primary_mode: Literal["demo", "neuuf"] = "demo"

    #: ``bedrock`` = Bedrock **Runtime** (``converse``) via Strands ``BedrockModel`` (default).
    #: ``anthropic`` = direct Anthropic API (optional; install ``pip install -e ".[anthropic]"``).
    llm_provider: Literal["anthropic", "bedrock"] = "bedrock"

    #: Bedrock ``modelId`` / inference profile. Empty → Strands regional default. Env:
    #: ``ISO_AGENT_BEDROCK_MODEL_ID``.
    bedrock_model_id: str = ""

    #: Bedrock region (e.g. ``us-east-1``). Empty → ``AWS_REGION`` / session / Strands default. Env:
    #: ``ISO_AGENT_BEDROCK_REGION_NAME``.
    bedrock_region_name: str = ""

    #: Optional Bedrock ``maxTokens``. ``None`` = omit. Env: ``ISO_AGENT_BEDROCK_MAX_TOKENS``.
    bedrock_max_tokens: int | None = None

    #: Anthropic ``model_id`` (Messages API). Environment: ``ISO_AGENT_ANTHROPIC_MODEL_ID``.
    anthropic_model_id: str = "claude-sonnet-4-6"

    #: Max tokens for Anthropic generations. Environment: ``ISO_AGENT_ANTHROPIC_MAX_TOKENS``.
    anthropic_max_tokens: int = 4096

    #: ``docker`` + ``PERPLEXITY_API_KEY`` starts Perplexity MCP (Phase 2).
    #: ``disabled`` never opens Docker.
    perplexity_transport: Literal["docker", "disabled"] = "disabled"

    #: Google Drive read-only tools on the coordinator (Phase 3).
    drive_enabled: bool = False

    #: Comma-separated Drive folder IDs that may be listed or used as parent allowlist.
    drive_allowed_folder_ids: str = ""

    #: Optional comma-separated file IDs readable even if parent checks differ.
    drive_allowed_file_ids: str = ""

    #: Max files returned by ``drive_list_folder`` (capped at 100).
    drive_max_list: int = 25

    #: Notion QMS tools on the coordinator (Phase 4).
    notion_enabled: bool = False

    #: Comma-separated Notion **page** UUIDs where **child drafts** may be created.
    notion_allowed_parent_ids: str = ""

    #: Comma-separated Notion **page** UUIDs that may be read via ``notion_read_page``.
    notion_allowed_page_ids: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
