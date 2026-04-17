"""Notion QMS tools (Phase 4): draft pages, read allowlisted pages, persisted allowlists."""

from __future__ import annotations

import logging
import os
from typing import Any

from strands.tools.decorator import tool

from iso_agent.config import get_settings
from iso_agent.l2_user import notion_allowlist_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client

logger = logging.getLogger(__name__)


def build_notion_tools(scope: UserScope) -> list[Any]:
    """Build Notion tools when enabled and ``NOTION_TOKEN`` is present.

    Read/draft allowlists are ``ISO_AGENT_NOTION_ALLOWED_*`` merged with per-user disk
    (``memory/users/<user_key>/notion/allowlist.json``). Tools are registered even when
    merged lists are empty so the agent can bootstrap via ``notion_allowlist_*`` and discovery.
    """
    settings = get_settings()
    if not settings.notion_enabled:
        return []

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        logger.warning("notion=token_missing | NOTION_TOKEN unset")
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

    tools_out: list[Any] = []

    if settings.notion_discovery_enabled:
        @tool(
            name="notion_discover_connected_pages",
            description=(
                "Read-only discovery: list Notion pages this integration can access "
                "(id, title, parent, url) via the search API. Optional query narrows results. "
                "Scope is pages shared with this integration in the Notion UI—not the draft "
                "parent allowlist. Use ids from here with notion_allowlist_add_read_page or "
                "notion_allowlist_add_draft_parent."
            ),
        )
        def notion_discover_connected_pages(query: str = "", max_pages: int = 25) -> str:
            """List accessible pages (read-only)."""
            try:
                max_n = int(max_pages)
            except (TypeError, ValueError):
                max_n = 25
            max_pages = max(1, min(max_n, 100))
            logger.debug(
                "notion_discover_connected_pages user_key=<%s> query_len=<%d>",
                scope.user_key,
                len(query.strip()),
            )
            try:
                hits = notion_client.search_connected_pages(
                    client, query=query, page_size=max_pages
                )
            except Exception as exc:
                logger.warning(
                    "notion=discover_failed exc_type=<%s>",
                    type(exc).__name__,
                    exc_info=exc,
                )
                return "error=discover_failed | check NOTION_TOKEN and page connections"
            if not hits:
                return (
                    "empty_results | connect at least one page to this integration "
                    "(Notion: page ... → Connections → your integration)"
                )
            lines: list[str] = []
            for page in hits[:max_pages]:
                pid = str(page.get("id", ""))
                url = str(page.get("url", ""))
                title = notion_client.page_plain_title(page)
                parent = page.get("parent", {})
                lines.append(f"id={pid} | title={title!r} | parent={parent} | url={url}")
            return "\n".join(lines)

        tools_out.append(notion_discover_connected_pages)

    @tool(
        name="notion_allowlist_list",
        description=(
            "Show Notion read/draft allowlist counts: environment vars, persisted file for this "
            "user, and merged totals (no secrets). Path is under memory/users/.../notion/."
        ),
    )
    def notion_allowlist_list() -> str:
        """Return allowlist status string."""
        s = get_settings()
        return notion_allowlist_store.format_allowlist_status(scope, s)

    @tool(
        name="notion_allowlist_add_read_page",
        description=(
            "Allow reading a Notion page by id: verifies the integration can retrieve the page, "
            "then appends the id to this user's persisted read allowlist (disk). Merged with "
            "ISO_AGENT_NOTION_ALLOWED_PAGE_IDS."
        ),
    )
    def notion_allowlist_add_read_page(page_id: str) -> str:
        """Persist one page id for notion_read_page after Notion confirms access."""
        if not notion_client.is_valid_notion_id(page_id):
            return "error=invalid_page_id"
        try:
            page_norm = notion_client.normalize_notion_page_id(page_id)
        except ValueError:
            return "error=invalid_page_id"
        if not notion_client.page_exists(client, page_id=page_norm):
            return (
                "error=page_not_accessible | connect the page to this integration or fix the id"
            )
        ok, code = notion_allowlist_store.add_persisted_read_page(scope, page_norm)
        if not ok:
            return f"error={code}"
        return f"ok=added_read_page page_id=<{page_norm}> | call notion_allowlist_list to verify"

    @tool(
        name="notion_allowlist_add_draft_parent",
        description=(
            "Allow creating draft child pages under this Notion parent page id: verifies "
            "retrieve, then appends to persisted draft-parent allowlist. Merged with "
            "ISO_AGENT_NOTION_ALLOWED_PARENT_IDS."
        ),
    )
    def notion_allowlist_add_draft_parent(parent_page_id: str) -> str:
        """Persist one parent id for notion_create_qms_draft after Notion confirms access."""
        if not notion_client.is_valid_notion_id(parent_page_id):
            return "error=invalid_parent_page_id"
        try:
            parent_norm = notion_client.normalize_notion_page_id(parent_page_id)
        except ValueError:
            return "error=invalid_parent_page_id"
        if not notion_client.page_exists(client, page_id=parent_norm):
            return (
                "error=parent_not_accessible | connect the page to this integration or fix the id"
            )
        ok, code = notion_allowlist_store.add_persisted_draft_parent(scope, parent_norm)
        if not ok:
            return f"error={code}"
        return (
            f"ok=added_draft_parent parent_page_id=<{parent_norm}> | "
            "call notion_allowlist_list to verify"
        )

    @tool(
        name="notion_allowlist_remove_read_page",
        description=(
            "Remove a page id from this user's **persisted** read allowlist only. Ids supplied "
            "only via ISO_AGENT_NOTION_ALLOWED_PAGE_IDS must be changed in deployment config."
        ),
    )
    def notion_allowlist_remove_read_page(page_id: str) -> str:
        """Drop one read page id from disk allowlist."""
        if not notion_client.is_valid_notion_id(page_id):
            return "error=invalid_page_id"
        try:
            page_norm = notion_client.normalize_notion_page_id(page_id)
        except ValueError:
            return "error=invalid_page_id"
        ok, code = notion_allowlist_store.remove_persisted_read_page(scope, page_norm)
        if not ok:
            return (
                f"error={code} | if the id is only in ISO_AGENT_NOTION_ALLOWED_PAGE_IDS "
                "remove it from the environment instead"
            )
        return f"ok=removed_read_page page_id=<{page_norm}>"

    @tool(
        name="notion_allowlist_remove_draft_parent",
        description=(
            "Remove a parent id from this user's **persisted** draft-parent allowlist only."
        ),
    )
    def notion_allowlist_remove_draft_parent(parent_page_id: str) -> str:
        """Drop one draft parent id from disk allowlist."""
        if not notion_client.is_valid_notion_id(parent_page_id):
            return "error=invalid_parent_page_id"
        try:
            parent_norm = notion_client.normalize_notion_page_id(parent_page_id)
        except ValueError:
            return "error=invalid_parent_page_id"
        ok, code = notion_allowlist_store.remove_persisted_draft_parent(scope, parent_norm)
        if not ok:
            return (
                f"error={code} | if the id is only in ISO_AGENT_NOTION_ALLOWED_PARENT_IDS "
                "remove it from the environment instead"
            )
        return f"ok=removed_draft_parent parent_page_id=<{parent_norm}>"

    tools_out.extend(
        [
            notion_allowlist_list,
            notion_allowlist_add_read_page,
            notion_allowlist_add_draft_parent,
            notion_allowlist_remove_read_page,
            notion_allowlist_remove_draft_parent,
        ]
    )

    @tool(
        name="notion_create_qms_draft",
        description=(
            "Create a **draft** child page under an allowlisted Notion parent (env or persisted). "
            "Optional drive_link is appended for traceability. If blocked, use "
            "notion_allowlist_add_draft_parent after discovery."
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
        try:
            parent_norm = notion_client.normalize_notion_page_id(parent_page_id)
        except ValueError:
            return "error=invalid_parent_page_id"
        s = get_settings()
        parents_merged = notion_allowlist_store.merged_parent_ids(scope, s)
        if not parents_merged:
            return (
                "error=no_draft_parent_allowlist | set ISO_AGENT_NOTION_ALLOWED_PARENT_IDS and/or "
                "call notion_allowlist_add_draft_parent (after notion_discover_connected_pages "
                "if discovery is enabled)"
            )
        if parent_norm not in parents_merged:
            return "error=parent_not_allowlisted"
        safe_title = f"[DRAFT] {title.strip()}"[:2000]
        text = body.strip()
        if drive_link.strip():
            text = f"{text}\n\n---\nDrive evidence: {drive_link.strip()}"
        try:
            created = notion_client.create_child_page(
                client,
                parent_page_id=parent_norm,
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
        description=(
            "Read plain text from an allowlisted Notion page (env or persisted). If blocked, "
            "use notion_allowlist_add_read_page."
        ),
    )
    def notion_read_page(page_id: str) -> str:
        """Fetch page content as text."""
        logger.debug("notion_read_page user_key=<%s> page_id=<%s>", scope.user_key, page_id)
        if not notion_client.is_valid_notion_id(page_id):
            return "error=invalid_page_id"
        try:
            page_norm = notion_client.normalize_notion_page_id(page_id)
        except ValueError:
            return "error=invalid_page_id"
        s = get_settings()
        pages_merged = notion_allowlist_store.merged_page_ids(scope, s)
        if not pages_merged:
            return (
                "error=no_read_allowlist | set ISO_AGENT_NOTION_ALLOWED_PAGE_IDS and/or call "
                "notion_allowlist_add_read_page (after notion_discover_connected_pages if "
                "discovery is enabled)"
            )
        if page_norm not in pages_merged:
            return "error=page_not_allowlisted"
        try:
            text = notion_client.fetch_page_text(client, page_id=page_norm)
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

    tools_out.extend([notion_create_qms_draft, notion_read_page])

    file_pages, file_parents = notion_allowlist_store.load_persisted_allowlist(scope)
    merged_p = notion_allowlist_store.merged_page_ids(scope, settings)
    merged_par = notion_allowlist_store.merged_parent_ids(scope, settings)
    logger.info(
        "notion=tools_built user_key=<%s> discovery=<%s> file_read=<%d> file_draft_parent=<%d> "
        "merged_read=<%d> merged_draft_parent=<%d>",
        scope.user_key,
        settings.notion_discovery_enabled,
        len(file_pages),
        len(file_parents),
        len(merged_p),
        len(merged_par),
    )
    return tools_out
