"""Notion QMS tools (Phase 4): draft pages, read allowlisted pages, persisted allowlists."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from strands.tools.decorator import tool

from iso_agent.config import get_settings
from iso_agent.l2_user import notion_allowlist_store, notion_page_index_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client, notion_mcp

logger = logging.getLogger(__name__)

_NOTION_TRACE_STDERR_READY = False


def _ensure_notion_trace_stderr() -> None:
    """Send ``notion_trace`` INFO logs to stderr when root logging is WARNING (common CLI default)."""
    global _NOTION_TRACE_STDERR_READY
    if _NOTION_TRACE_STDERR_READY:
        return
    if logger.handlers:
        _NOTION_TRACE_STDERR_READY = True
        return
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler(sys.stderr)
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_h)
    logger.propagate = False
    _NOTION_TRACE_STDERR_READY = True


def build_notion_tools(scope: UserScope) -> list[Any]:
    """Build Notion tools when ``NOTION_TOKEN`` is present (``notion_enabled`` defaults on).

    Set ``ISO_AGENT_NOTION_ENABLED=false`` to disable Notion tools entirely. Read/draft
    allowlists are ``ISO_AGENT_NOTION_ALLOWED_*`` merged with per-user disk
    (``memory/users/<user_key>/notion/allowlist.json``). Tools are registered even when
    merged lists are empty so the agent can bootstrap via ``notion_allowlist_*`` and discovery.
    """
    settings = get_settings()
    _discovery_effective = settings.notion_discovery_enabled
    if notion_mcp.notion_mcp_primary_hides_rest_discovery(scope):
        _discovery_effective = False
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
    _ensure_notion_trace_stderr()

    if _discovery_effective:
        @tool(
            name="notion_discover_connected_pages",
            description=(
                "Read-only discovery: list Notion pages this integration can access "
                "(id, title, parent, url) via the search API. Optional query narrows results. "
                "Scope is pages shared with this integration in the Notion UI—not the draft "
                "parent allowlist. For notion_allowlist_add_read_page / add_draft_parent, copy "
                "the exact id=... from these lines (do not invent ids from titles or URLs). "
                "To persist a searchable copy under memory/users/.../notion/, call "
                "notion_refresh_page_index."
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
                idx_n = len(notion_page_index_store.load_index(scope).entries)
                logger.info(
                    "notion_trace discover user_key=<%s> hit_count=0 disk_index_entries=<%d>",
                    scope.user_key,
                    idx_n,
                )
                base = (
                    "empty_results | connect at least one page to this integration "
                    "(Notion: page ... → Connections → your integration)"
                )
                if idx_n:
                    return (
                        f"{base} | stale_disk_index | on_disk_entries=<{idx_n}> — run "
                        "notion_refresh_page_index now (it replaces the file with live search; "
                        "zero hits clears stale UUIDs). Do not trust notion_search_page_index until "
                        "then."
                    )
                return base
            logger.info(
                "notion_trace discover user_key=<%s> hit_count=<%d>",
                scope.user_key,
                len(hits),
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
            "ISO_AGENT_NOTION_ALLOWED_PAGE_IDS. Pass the exact id=... from "
            "notion_discover_connected_pages / notion_refresh_page_index output (32 hex), "
            "not a title or full browser URL."
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
        ok_ret, diag = notion_client.page_retrieve_diagnostic(client, page_id=page_norm)
        if not ok_ret:
            logger.info(
                "notion_trace allowlist_add_read user_key=<%s> outcome=not_accessible detail=<%s>",
                scope.user_key,
                diag,
            )
            return (
                "error=page_not_accessible | pages.retrieve failed "
                f"({diag}). "
                "If notion_discover_connected_pages just listed this page, the usual fix is to "
                "pass the exact id=... from that tool output (copy the UUID only)—not the title "
                "or slug from a browser URL. If the id matches and this still fails, check Notion "
                "⋯→Connections or NOTION_TOKEN workspace."
            )
        ok, code = notion_allowlist_store.add_persisted_read_page(scope, page_norm)
        if not ok:
            return f"error={code}"
        return f"ok=added_read_page page_id=<{page_norm}> | call notion_allowlist_list to verify"

    def _add_draft_parent_normalized(parent_norm: str) -> str:
        """Verify Notion access and append ``parent_norm`` to the persisted draft-parent list."""
        ok_ret, diag = notion_client.page_retrieve_diagnostic(client, page_id=parent_norm)
        if not ok_ret:
            logger.info(
                "notion_trace allowlist_add_draft_parent user_key=<%s> outcome=not_accessible "
                "detail=<%s>",
                scope.user_key,
                diag,
            )
            return (
                "error=parent_not_accessible | pages.retrieve failed "
                f"({diag}). "
                "Use the exact id=... from discovery/index output for this parent page. "
                "If the id is correct and this still fails, check Notion ⋯→Connections or token."
            )
        ok, code = notion_allowlist_store.add_persisted_draft_parent(scope, parent_norm)
        if not ok:
            return f"error={code}"
        return (
            f"ok=added_draft_parent parent_page_id=<{parent_norm}> | "
            "call notion_allowlist_list to verify"
        )

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
        return _add_draft_parent_normalized(parent_norm)

    @tool(
        name="notion_bootstrap_draft_parent_choices",
        description=(
            "When no (or wrong) draft parents are configured, list **numbered** candidate pages "
            "from the persisted index (workspace-top-level sorts first). Optional **search_text** "
            "filters titles. Human picks **choice**; coordinator calls "
            "**notion_allowlist_add_draft_parent_by_choice** with the **same** search_text and "
            "max_options—no UUID pasting required."
        ),
    )
    def notion_bootstrap_draft_parent_choices(search_text: str = "", max_options: int = 12) -> str:
        """Numbered menu of index pages suitable for becoming draft parents."""
        try:
            mo = int(max_options)
        except (TypeError, ValueError):
            mo = 12
        mo = max(1, min(mo, 50))
        entries = notion_page_index_store.bootstrap_draft_parent_candidates(
            scope, title_needle=search_text, max_results=mo
        )
        if not entries:
            return (
                "empty | call notion_refresh_page_index first or widen search_text | "
                "for by_choice repeat the same search_text and max_options you will use next"
            )
        s = get_settings()
        parents = notion_allowlist_store.merged_parent_ids(scope, s)
        header = (
            f"repeat_params | search_text={search_text!r} | max_options={mo} | "
            "next_tool=notion_allowlist_add_draft_parent_by_choice"
        )
        lines = [header]
        for i, e in enumerate(entries, start=1):
            w = "yes" if notion_page_index_store.is_workspace_parent_entry(e) else "no"
            ad = "yes" if e.id in parents else "no"
            lines.append(
                f"choice={i} | id={e.id} | title={e.title!r} | url={e.url} | "
                f"top_level_workspace_parent={w} | already_draft_parent={ad}"
            )
        return "\n".join(lines)

    @tool(
        name="notion_allowlist_add_draft_parent_by_choice",
        description=(
            "Add a draft parent using **choice** from the latest "
            "**notion_bootstrap_draft_parent_choices** output. **search_text** and **max_options** "
            "must match that call exactly (deterministic replay). Then create drafts with "
            "**notion_create_qms_draft_for_parent_title**."
        ),
    )
    def notion_allowlist_add_draft_parent_by_choice(
        choice: int, search_text: str = "", max_options: int = 12
    ) -> str:
        """Persist draft parent id selected from the numbered bootstrap list."""
        try:
            mo = int(max_options)
        except (TypeError, ValueError):
            mo = 12
        mo = max(1, min(mo, 50))
        entries = notion_page_index_store.bootstrap_draft_parent_candidates(
            scope, title_needle=search_text, max_results=mo
        )
        if not entries:
            return "error=empty_candidates | run bootstrap after notion_refresh_page_index"
        if choice < 1 or choice > len(entries):
            return f"error=invalid_choice | valid_range=1..{len(entries)}"
        parent_norm = entries[choice - 1].id
        logger.debug(
            "notion_add_draft_parent_by_choice user_key=<%s> choice=<%d> parent=<%s>",
            scope.user_key,
            choice,
            parent_norm,
        )
        return _add_draft_parent_normalized(parent_norm)

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

    @tool(
        name="notion_refresh_page_index",
        description=(
            "Replace the persisted page index with this run's Notion **search** results "
            "(``memory/users/<user_key>/notion/discovered_page_index.json``). Same API as "
            "notion_discover_connected_pages; stale ids from older refreshes are dropped. "
            "**Best practice:** (1) For **listing everything under one hub page** (true subtree), "
            "use a **broad** refresh first—**query** empty string and **max_pages** high "
            "(e.g. 100)—then **notion_page_index_subtree(parent_page_id=hub id)**. A **narrow** "
            "**query** replaces the whole index with only those search hits, so child pages whose "
            "titles do not match the query **vanish** from the index (e.g. Project Tracker missing). "
            "(2) For **finding** pages by phrase, set **query** to that phrase, then outline/search. "
            "Then use notion_allowlist_add_draft_parent as needed."
        ),
    )
    def notion_refresh_page_index(query: str = "", max_pages: int = 100) -> str:
        """Replace on-disk page index with this run's search results (may be zero)."""
        try:
            max_n = int(max_pages)
        except (TypeError, ValueError):
            max_n = 100
        max_pages = max(1, min(max_n, 100))
        logger.debug(
            "notion_refresh_page_index user_key=<%s> query_len=<%d> max_pages=<%d>",
            scope.user_key,
            len(query.strip()),
            max_pages,
        )
        try:
            hits = notion_client.search_connected_pages(
                client, query=query, page_size=max_pages
            )
        except Exception as exc:
            logger.warning(
                "notion=index_refresh_failed exc_type=<%s>",
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=search_failed | check NOTION_TOKEN and page connections"
        if not hits:
            # Always persist (even zero hits) so a stale on-disk index is replaced when live
            # search returns nothing—otherwise old UUIDs mislead bootstrap/allowlist_add.
            logger.info(
                "notion_trace refresh user_key=<%s> search_hit_count=0 clearing_disk_index",
                scope.user_key,
            )
            n = notion_page_index_store.merge_discovery_hits(scope, [])
            status = notion_page_index_store.format_status(scope)
            logger.info(
                "notion_trace refresh user_key=<%s> merged_entries=<%d> status=<%s>",
                scope.user_key,
                n,
                status,
            )
            qshow = query.strip() or "(empty)"
            return (
                f"ok=index_cleared merged_entries=<{n}> | {status} | search_query_used=<{qshow}> | "
                "live_search_returned_zero_pages — connect this integration on pages in Notion "
                "(⋯ → Connections), verify NOTION_TOKEN, widen or change query, then refresh again"
            )
        logger.info(
            "notion_trace refresh user_key=<%s> search_hit_count=<%d>",
            scope.user_key,
            len(hits),
        )
        n = notion_page_index_store.merge_discovery_hits(scope, hits)
        status = notion_page_index_store.format_status(scope)
        logger.info(
            "notion_trace refresh user_key=<%s> merged_entries=<%d> status=<%s>",
            scope.user_key,
            n,
            status,
        )
        qshow = query.strip() or "(empty)"
        return f"ok=index_refreshed merged_entries=<{n}> | {status} | search_query_used=<{qshow}>"

    @tool(
        name="notion_search_page_index",
        description=(
            "Search the persisted page index (case-insensitive). Default: ``search_text`` is a "
            "single substring on titles. Set match_all_words=true to require every whitespace-"
            "separated token in the title (narrows 'engineering' vs 'corporate engineering'). "
            "Returns id, title, url lines. Call notion_refresh_page_index first if entries=0; "
            "use notion_page_index_outline for workspace vs nested context."
        ),
    )
    def notion_search_page_index(
        search_text: str, max_results: int = 25, match_all_words: bool = False
    ) -> str:
        """Lookup pages by title against the local index."""
        try:
            mr = int(max_results)
        except (TypeError, ValueError):
            mr = 25
        mr = max(1, min(mr, 50))
        maw = bool(match_all_words)
        hits = notion_page_index_store.search_titles(
            scope, search_text, max_results=mr, match_all_words=maw
        )
        if not hits:
            return (
                "empty_results | call notion_refresh_page_index or check spelling; "
                "index only contains pages returned by the last refresh(es)"
            )
        lines = [f"id={e.id} | title={e.title!r} | url={e.url}" for e in hits]
        return "\n".join(lines)

    @tool(
        name="notion_page_index_status",
        description=(
            "Show path and entry count for the persisted Notion discovery index (no secrets)."
        ),
    )
    def notion_page_index_status() -> str:
        """Return index file status."""
        return notion_page_index_store.format_status(scope)

    @tool(
        name="notion_page_index_outline",
        description=(
            "Structured view of the persisted index: (1) workspace top-level pages "
            "(parent.type=workspace), (2) nested pages with parent_page_id and parent_title "
            "resolved from the same snapshot when possible. Run **after** "
            "notion_refresh_page_index—ideally a **targeted** refresh whose **query** matches "
            "the user’s team/space phrase so the snapshot is current and scoped. Does not call "
            "Notion again."
        ),
    )
    def notion_page_index_outline(max_lines: int = 120) -> str:
        """Summarize index rows grouped by workspace vs nested parent context."""
        try:
            ml = int(max_lines)
        except (TypeError, ValueError):
            ml = 120
        ml = max(20, min(ml, 300))
        return notion_page_index_store.format_index_outline(scope, max_lines=ml)

    @tool(
        name="notion_page_index_subtree",
        description=(
            "List the hub page plus every **descendant** row in the persisted index whose "
            "parent.page_id chain reaches **parent_page_id** (within that snapshot only). "
            "Use after a **broad** notion_refresh_page_index (query empty, high max_pages) so "
            "children exist in the index. Does not call Notion. Many workspace-visible pages are "
            "siblings at parent.type=workspace in the API—this tool only follows parent_page_id "
            "links in the index, not every page visible in the Notion UI sidebar."
        ),
    )
    def notion_page_index_subtree(parent_page_id: str, max_lines: int = 120) -> str:
        """Show hub + descendants from the on-disk index graph."""
        try:
            ml = int(max_lines)
        except (TypeError, ValueError):
            ml = 120
        ml = max(20, min(ml, 300))
        return notion_page_index_store.format_subtree_under_parent(
            scope, parent_page_id, max_lines=ml
        )

    @tool(
        name="notion_page_metadata",
        description=(
            "Show **parent JSON**, title, url, and optional **last_edited_time** from the "
            "persisted index row, plus an **ancestor_titles_top_down** chain inferred only from "
            "index parent_page_id links (hub → … → this page). Notion does not expose sidebar "
            "grouping when parent.type is workspace—use this chain and notion_page_index_subtree "
            "for structure. Set include_live_retrieve=true for one "
            "pages.retrieve (parent, times, property **keys** only—no property values)."
        ),
    )
    def notion_page_metadata(page_id: str, include_live_retrieve: bool = False) -> str:
        """Index metadata plus optional live API summary."""
        if not notion_client.is_valid_notion_id(page_id):
            return "error=invalid_page_id"
        try:
            page_norm = notion_client.normalize_notion_page_id(page_id)
        except ValueError:
            return "error=invalid_page_id"
        live: dict[str, Any] | None = None
        if include_live_retrieve:
            ok, diag = notion_client.page_retrieve_diagnostic(client, page_id=page_norm)
            if not ok:
                return f"error=live_retrieve_failed | {diag}"
            live = notion_client.fetch_page_summary(client, page_id=page_norm)
        return notion_page_index_store.format_page_metadata_report(
            scope, page_norm, live_summary=live
        )

    def _create_qms_draft_at_parent_norm(
        parent_norm: str, title: str, body: str, drive_link: str
    ) -> str:
        """Shared create path after ``parent_norm`` is validated against merged draft parents."""
        s = get_settings()
        parents_merged = notion_allowlist_store.merged_parent_ids(scope, s)
        if not parents_merged:
            return (
                "error=no_draft_parent_allowlist | set ISO_AGENT_NOTION_ALLOWED_PARENT_IDS and/or "
                "call notion_allowlist_add_draft_parent (after notion_discover_connected_pages "
                "if discovery is enabled)"
            )
        if parent_norm not in parents_merged:
            return (
                "error=parent_not_allowlisted | parent_page_id is not in merged_draft_parent "
                "allowlist (env ∪ disk)—separate from Notion Connections; use "
                "notion_allowlist_add_draft_parent when the API can already see the parent"
            )
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
                parent_norm,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=create_failed | check integration capabilities and parent id"
        pid = str(created.get("id", ""))
        url = str(created.get("url", ""))
        return f"page_id={pid}\nurl={url}"

    @tool(
        name="notion_list_draft_parents",
        description=(
            "List merged **draft parent** page ids with titles from the local page index—no manual "
            "UUID pasting for humans. Run notion_refresh_page_index if titles show as missing."
        ),
    )
    def notion_list_draft_parents() -> str:
        """Show allowlisted draft parents with titles."""
        s = get_settings()
        rows = notion_page_index_store.iter_merged_draft_parents_with_titles(scope, s)
        if not rows:
            return (
                "empty | no draft parents in merged allowlist | run "
                "notion_bootstrap_draft_parent_choices (after notion_refresh_page_index) or "
                "notion_allowlist_add_draft_parent / notion_allowlist_add_draft_parent_by_choice"
            )
        return "\n".join(f"id={p} | title={t!r}" for p, t in rows)

    @tool(
        name="notion_list_pages_under_parent",
        description=(
            "List pages under a **parent** using only the persisted index (no new Notion search). "
            "Supply **parent_page_id** OR **parent_title_substring** (unique match among merged "
            "draft parents **and** merged read pages). Optional **child_title_filter** narrows "
            "children. Refresh the index first so parent/child rows exist."
        ),
    )
    def notion_list_pages_under_parent(
        parent_title_substring: str = "",
        parent_page_id: str = "",
        child_title_filter: str = "",
        max_results: int = 50,
    ) -> str:
        """List index entries whose Notion parent matches an allowlisted anchor page."""
        s = get_settings()
        parents = notion_allowlist_store.merged_parent_ids(scope, s)
        pages = notion_allowlist_store.merged_page_ids(scope, s)
        anchors = parents | pages
        if not anchors:
            return (
                "error=no_allowlist | add read pages and/or draft parents before "
                "browsing the index tree"
            )
        parent_norm: str | None = None
        if parent_page_id.strip():
            if not notion_client.is_valid_notion_id(parent_page_id):
                return "error=invalid_parent_page_id"
            try:
                parent_norm = notion_client.normalize_notion_page_id(parent_page_id)
            except ValueError:
                return "error=invalid_parent_page_id"
            if parent_norm not in anchors:
                return "error=parent_anchor_not_allowlisted"
        elif parent_title_substring.strip():
            resolved, err = notion_page_index_store.resolve_unique_page_id_by_title_hint(
                scope, anchors, parent_title_substring, label="draft_parents_or_read_pages"
            )
            if not resolved:
                return err
            parent_norm = resolved
        else:
            return "error=need_parent_page_id_or_parent_title_substring"
        try:
            mr = int(max_results)
        except (TypeError, ValueError):
            mr = 50
        children = notion_page_index_store.list_index_children_of_parent(
            scope,
            parent_id=parent_norm,
            title_needle=child_title_filter,
            max_results=mr,
        )
        if not children:
            return (
                f"empty_children | parent={parent_norm} | index may be stale—run "
                f"notion_refresh_page_index or widen discovery"
            )
        lines = [f"id={e.id} | title={e.title!r} | url={e.url}" for e in children]
        return "\n".join(lines)

    @tool(
        name="notion_create_qms_draft_for_parent_title",
        description=(
            "Create a draft like notion_create_qms_draft but resolve the parent by **unique** "
            "**parent_title_substring** against merged draft parents (titles from the local "
            "index). Avoids pasting raw UUIDs in user chat when titles are distinctive."
        ),
    )
    def notion_create_qms_draft_for_parent_title(
        parent_title_substring: str,
        title: str,
        body: str,
        drive_link: str = "",
    ) -> str:
        """Create a QMS draft under the draft parent whose title uniquely matches the hint."""
        s = get_settings()
        parents = notion_allowlist_store.merged_parent_ids(scope, s)
        resolved, err = notion_page_index_store.resolve_unique_page_id_by_title_hint(
            scope, parents, parent_title_substring, label="draft_parents"
        )
        if not resolved:
            return err
        logger.debug(
            "notion_create_draft_by_title user_key=<%s> parent_resolved=<%s>",
            scope.user_key,
            resolved,
        )
        return _create_qms_draft_at_parent_norm(resolved, title, body, drive_link)

    tools_out.extend(
        [
            notion_allowlist_list,
            notion_allowlist_add_read_page,
            notion_allowlist_add_draft_parent,
            notion_bootstrap_draft_parent_choices,
            notion_allowlist_add_draft_parent_by_choice,
            notion_allowlist_remove_read_page,
            notion_allowlist_remove_draft_parent,
            notion_refresh_page_index,
            notion_search_page_index,
            notion_page_index_status,
            notion_page_index_outline,
            notion_page_index_subtree,
            notion_page_metadata,
            notion_list_draft_parents,
            notion_list_pages_under_parent,
            notion_create_qms_draft_for_parent_title,
        ]
    )

    @tool(
        name="notion_create_qms_draft",
        description=(
            "Create a **draft** child page under an allowlisted Notion parent (env or persisted). "
            "Optional drive_link is appended for traceability. If blocked, use "
            "notion_allowlist_add_draft_parent after discovery. Prefer "
            "notion_create_qms_draft_for_parent_title when the human should not paste UUIDs."
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
        return _create_qms_draft_at_parent_norm(parent_norm, title, body, drive_link)

    @tool(
        name="notion_read_page",
        description=(
            "Read plain text from pages in merged **read allowlist** only (env ∪ disk)—an extra "
            "safety gate beyond Notion Connections. If error=page_not_allowlisted, call "
            "notion_allowlist_add_read_page with the same id when discovery shows the page."
        ),
    )
    def notion_read_page(page_id: str) -> str:
        """Fetch page content as text."""
        logger.debug("notion_read_page user_key=<%s> page_id=<%s>", scope.user_key, page_id)
        if not notion_client.is_valid_notion_id(page_id):
            logger.info("notion_trace read_page user_key=<%s> outcome=invalid_page_id", scope.user_key)
            return "error=invalid_page_id"
        try:
            page_norm = notion_client.normalize_notion_page_id(page_id)
        except ValueError:
            logger.info("notion_trace read_page user_key=<%s> outcome=invalid_page_id", scope.user_key)
            return "error=invalid_page_id"
        s = get_settings()
        pages_merged = notion_allowlist_store.merged_page_ids(scope, s)
        if not pages_merged:
            logger.info(
                "notion_trace read_page user_key=<%s> outcome=no_read_allowlist merged_read=0",
                scope.user_key,
            )
            return (
                "error=no_read_allowlist | set ISO_AGENT_NOTION_ALLOWED_PAGE_IDS and/or call "
                "notion_allowlist_add_read_page (after notion_discover_connected_pages if "
                "discovery is enabled)"
            )
        if page_norm not in pages_merged:
            logger.info(
                "notion_trace read_page user_key=<%s> outcome=not_allowlisted merged_read=<%d>",
                scope.user_key,
                len(pages_merged),
            )
            return (
                "error=page_not_allowlisted | this page_id is not in merged_read_allowlist "
                "(env ISO_AGENT_NOTION_ALLOWED_PAGE_IDS ∪ persisted allowlist)—separate from "
                "Notion ⋯→Connections. If discovery/index already shows this page, call "
                "notion_allowlist_add_read_page(page_id) (no Connections change needed)."
            )
        try:
            text = notion_client.fetch_page_text(client, page_id=page_norm)
        except Exception as exc:
            logger.warning(
                "notion=read_failed page_id=<%s> exc_type=<%s>",
                page_id,
                type(exc).__name__,
                exc_info=exc,
            )
            logger.info(
                "notion_trace read_page user_key=<%s> outcome=read_failed exc_type=<%s>",
                scope.user_key,
                type(exc).__name__,
            )
            return "error=read_failed"
        if not text:
            logger.info("notion_trace read_page user_key=<%s> outcome=empty_page", scope.user_key)
            return "empty_page"
        max_out = 24000
        if len(text) > max_out:
            logger.info(
                "notion_trace read_page user_key=<%s> outcome=ok_truncated text_len=<%d>",
                scope.user_key,
                len(text),
            )
            return text[:max_out] + "\n...truncated..."
        logger.info(
            "notion_trace read_page user_key=<%s> outcome=ok text_len=<%d>",
            scope.user_key,
            len(text),
        )
        return text

    tools_out.extend([notion_create_qms_draft, notion_read_page])

    file_pages, file_parents = notion_allowlist_store.load_persisted_allowlist(scope)
    merged_p = notion_allowlist_store.merged_page_ids(scope, settings)
    merged_par = notion_allowlist_store.merged_parent_ids(scope, settings)
    index_n = len(notion_page_index_store.load_index(scope).entries)
    logger.info(
        "notion=tools_built user_key=<%s> discovery=<%s> file_read=<%d> file_draft_parent=<%d> "
        "merged_read=<%d> merged_draft_parent=<%d> page_index_entries=<%d>",
        scope.user_key,
        settings.notion_discovery_enabled,
        len(file_pages),
        len(file_parents),
        len(merged_p),
        len(merged_par),
        index_n,
    )
    return tools_out
