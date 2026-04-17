"""Notion QMS tools (Phase 4): draft pages and read allowlisted pages."""

from __future__ import annotations

import logging
import os
from typing import Any

from strands.tools.decorator import tool

from iso_agent.config import get_settings
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client

logger = logging.getLogger(__name__)


def _parse_uuid_set(raw: str) -> set[str]:
    return {part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()}


def build_notion_tools(scope: UserScope) -> list[Any]:
    """Build Notion tools when enabled, token present, and allowlists are non-empty."""
    settings = get_settings()
    if not settings.notion_enabled:
        return []

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        logger.warning("notion=token_missing | NOTION_TOKEN unset")
        return []

    parents = _parse_uuid_set(settings.notion_allowed_parent_ids)
    pages = _parse_uuid_set(settings.notion_allowed_page_ids)
    if not parents and not pages:
        logger.warning(
            "notion=allowlist_empty | set ISO_AGENT_NOTION_ALLOWED_PARENT_IDS "
            "and/or ISO_AGENT_NOTION_ALLOWED_PAGE_IDS",
        )
        return []

    try:
        client = notion_client.build_notion_client(token)
    except ImportError as exc:
        logger.warning(
            "notion=import_failed hint=<%s> exc_type=<%s>",
            "pip install iso-agent[notion]",
            type(exc).__name__,
            exc_info=exc,
        )
        return []
    except Exception as exc:
        logger.warning("notion=client_failed exc_type=<%s>", type(exc).__name__, exc_info=exc)
        return []

    @tool(
        name="notion_create_qms_draft",
        description=(
            "Create a **draft** child page under an allowlisted Notion parent. "
            "Optional drive_link is appended for traceability."
        ),
    )
    def notion_create_qms_draft(
        parent_page_id: str,
        title: str,
        body: str,
        drive_link: str = "",
    ) -> str:
        """Create a QMS draft page in Notion."""
        logger.debug(
            "notion_create_draft user_key=<%s> parent_page_id=<%s>",
            scope.user_key,
            parent_page_id,
        )
        if not notion_client.is_valid_notion_id(parent_page_id):
            return "error=invalid_parent_page_id"
        if parent_page_id not in parents:
            return "error=parent_not_allowlisted"
        safe_title = f"[DRAFT] {title.strip()}"[:2000]
        text = body.strip()
        if drive_link.strip():
            text = f"{text}\n\n---\nDrive evidence: {drive_link.strip()}"
        try:
            created = notion_client.create_child_page(
                client,
                parent_page_id=parent_page_id,
                title=safe_title,
                body=text or " ",
            )
        except Exception as exc:
            logger.warning(
                "notion=create_failed parent=<%s> exc_type=<%s>",
                parent_page_id,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=create_failed | check integration capabilities and parent id"
        pid = str(created.get("id", ""))
        url = str(created.get("url", ""))
        return f"page_id={pid}\nurl={url}"

    @tool(
        name="notion_read_page",
        description="Read plain text from an allowlisted Notion page (block children).",
    )
    def notion_read_page(page_id: str) -> str:
        """Fetch page content as text."""
        logger.debug("notion_read_page user_key=<%s> page_id=<%s>", scope.user_key, page_id)
        if not notion_client.is_valid_notion_id(page_id):
            return "error=invalid_page_id"
        if page_id not in pages:
            return "error=page_not_allowlisted"
        try:
            text = notion_client.fetch_page_text(client, page_id=page_id)
        except Exception as exc:
            logger.warning(
                "notion=read_failed page_id=<%s> exc_type=<%s>",
                page_id,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=read_failed"
        if not text:
            return "empty_page"
        max_out = 24000
        if len(text) > max_out:
            return text[:max_out] + "\n...truncated..."
        return text

    out: list[Any] = []
    if parents:
        out.append(notion_create_qms_draft)
    if pages:
        out.append(notion_read_page)
    return out
