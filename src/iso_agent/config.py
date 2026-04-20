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

    #: Bedrock model id; empty uses Strands / boto defaults. Env: ``ISO_AGENT_BEDROCK_MODEL_ID``.
    bedrock_model_id: str = ""

    #: Bedrock max tokens; ``None`` omits the kwarg. Env: ``ISO_AGENT_BEDROCK_MAX_TOKENS``.
    bedrock_max_tokens: int | None = None

    #: AWS region for Bedrock; empty uses SDK default chain. Env: ``ISO_AGENT_BEDROCK_REGION_NAME``.
    bedrock_region_name: str = ""

    #: ``docker`` + ``PERPLEXITY_API_KEY`` starts Perplexity MCP (Phase 2).
    #: ``disabled`` never opens Docker.
    perplexity_transport: Literal["docker", "disabled"] = "disabled"

    #: ``stdio`` spawns ``npx -y google-workspace-mcp serve`` (OAuth via
    #: ``npx google-workspace-mcp setup`` once; see integrations walkthrough).
    #: ``disabled`` (default) does not start MCP.
    google_workspace_mcp_transport: Literal["disabled", "stdio"] = "disabled"

    #: When transport is ``stdio``, append ``--read-only`` to ``serve`` (recommended).
    google_workspace_mcp_serve_read_only: bool = True

    #: Google Drive REST helpers (Phase 3). Used by ``drive_tools`` / tests only;
    #: the Neuuf coordinator does **not** register ``drive_*`` tools.
    drive_enabled: bool = True

    #: Comma-separated Drive folder IDs that may be listed or used as parent allowlist.
    drive_allowed_folder_ids: str = ""

    #: Optional comma-separated file IDs readable even if parent checks differ.
    drive_allowed_file_ids: str = ""

    #: Max files returned by ``drive_list_folder`` (capped at 100).
    drive_max_list: int = 25

    #: Notion QMS tools on the coordinator (Phase 4). Defaults ``true``; set
    #: ``ISO_AGENT_NOTION_ENABLED=false`` to omit Notion tools even when MCP OAuth is configured.
    notion_enabled: bool = True

    #: Comma-separated Notion **page** UUIDs where **child drafts** may be created.
    notion_allowed_parent_ids: str = ""

    #: Comma-separated Notion **page** UUIDs that may be read via ``notion_read_page``.
    notion_allowed_page_ids: str = ""

    #: When ``notion_enabled``, expose read-only ``notion_discover_connected_pages``
    #: (Notion search: pages the integration can access). Defaults ``true``; set
    #: ``ISO_AGENT_NOTION_DISCOVERY_ENABLED=false`` to hide that tool only.
    notion_discovery_enabled: bool = True

    #: ``hybrid`` / ``mcp_primary`` (default ``hybrid``): start hosted Notion MCP when
    #: ``mcp_oauth.json`` exists; ``notion_*`` tools call MCP under the hood.
    #: ``rest_only`` disables Notion tools entirely (no OAuth client).
    notion_transport: Literal["rest_only", "hybrid", "mcp_primary"] = "hybrid"

    #: Notion hosted MCP streamable HTTP URL (`Other tools` in Notion docs).
    notion_mcp_url: str = "https://mcp.notion.com/mcp"

    #: OAuth redirect URI (must match the localhost listener in ``iso-notion-mcp-login``).
    notion_mcp_redirect_uri: str = "http://127.0.0.1:8765/callback"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
