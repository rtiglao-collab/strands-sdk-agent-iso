"""Persisted snapshot of Notion pages visible to the integration (per user).

Stored next to the allowlist under ``memory/users/<user_key>/notion/``. Built from the same
search API as discovery; use for quick title→id lookup without re-querying every turn.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from iso_agent.config import Settings
from iso_agent.l2_user import notion_allowlist_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 300
_FILE_NAME = "discovered_page_index.json"


class PageIndexEntry(BaseModel):
    """One page row in the on-disk index."""

    id: str
    title: str = ""
    url: str = ""
    parent: dict[str, Any] = Field(default_factory=dict)
    last_edited_time: str = ""


class PersistedPageIndex(BaseModel):
    """On-disk shape for the discovery snapshot."""

    version: int = 1
    updated_at: str = ""
    entries: list[PageIndexEntry] = Field(default_factory=list)


def index_path(scope: UserScope) -> Path:
    """Path to ``discovered_page_index.json`` for this user."""
    return notion_allowlist_store.notion_allowlist_dir(scope) / _FILE_NAME


def load_index(scope: UserScope) -> PersistedPageIndex:
    """Load index from disk or return empty."""
    path = index_path(scope)
    if not path.is_file():
        return PersistedPageIndex()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PersistedPageIndex.model_validate(raw)
    except Exception as exc:
        logger.warning(
            "notion_page_index=load_failed path=<%s> exc_type=<%s>",
            path,
            type(exc).__name__,
            exc_info=exc,
        )
        return PersistedPageIndex()


def save_index(scope: UserScope, data: PersistedPageIndex) -> None:
    """Write index JSON."""
    path = index_path(scope)
    path.write_text(data.model_dump_json(indent=2) + "\n", encoding="utf-8")


def merge_discovery_hits(scope: UserScope, hits: list[dict[str, Any]]) -> int:
    """Persist this refresh's search hits as the page index (dedupe by id, cap size).

    Replaces the previous snapshot so ids that no longer appear in Notion search (or are no
    longer shared with the integration) do not linger and confuse bootstrap / draft-parent flows.
    """
    by_id: dict[str, PageIndexEntry] = {}
    for page in hits:
        pid = str(page.get("id", "")).strip()
        if not pid:
            continue
        try:
            nid = notion_client.normalize_notion_page_id(pid)
        except ValueError:
            continue
        parent = page.get("parent", {})
        if not isinstance(parent, dict):
            parent = {}
        by_id[nid] = PageIndexEntry(
            id=nid,
            title=notion_client.page_plain_title(page),
            url=str(page.get("url", "")),
            parent=parent,
            last_edited_time=str(page.get("last_edited_time", "") or ""),
        )
    entries = list(by_id.values())
    entries.sort(key=lambda e: e.title.lower())
    if len(entries) > _MAX_ENTRIES:
        entries = entries[:_MAX_ENTRIES]
    data = PersistedPageIndex(
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        entries=entries,
    )
    save_index(scope, data)
    return len(entries)


def search_titles(
    scope: UserScope,
    needle: str,
    *,
    max_results: int = 25,
    match_all_words: bool = False,
) -> list[PageIndexEntry]:
    """Return entries whose title matches ``needle`` (case-insensitive).

    Default: substring match on the full ``needle``. When ``match_all_words`` is True, split
    ``needle`` on whitespace and require **every** token to appear somewhere in the title (helps
    disambiguate e.g. "corporate engineering" vs pages titled only "Engineering …").
    """
    raw = needle.strip()
    if not raw:
        return []
    n = raw.lower()
    words: list[str] = []
    if match_all_words:
        words = [w for w in n.split() if w]
        if not words:
            return []
    out: list[PageIndexEntry] = []
    for e in load_index(scope).entries:
        t = e.title.lower()
        if match_all_words:
            if not all(w in t for w in words):
                continue
        elif n not in t:
            continue
        out.append(e)
        if len(out) >= max_results:
            break
    return out


def format_status(scope: UserScope) -> str:
    """One-line status for coordinator tools."""
    data = load_index(scope)
    rel = index_path(scope).relative_to(scope.memory_root)
    return (
        f"path=<{rel}> | entries=<{len(data.entries)}> | updated_at=<{data.updated_at or 'never'}>"
    )


def format_index_outline(scope: UserScope, *, max_lines: int = 120) -> str:
    """Human-readable snapshot: workspace top-level pages, then nested rows with parent titles.

    Data comes only from the last ``merge_discovery_hits`` / ``notion_refresh_page_index`` run.
    Parent titles for nested pages are resolved from other index rows when the parent id is
    present; otherwise ``(parent title not in index)``.
    """
    cap = max(20, min(int(max_lines), 300))
    data = load_index(scope)
    if not data.entries:
        return (
            "empty_index | run notion_refresh_page_index (or widen query) so this outline has "
            "rows to group"
        )
    entries = list(data.entries)
    roots = [e for e in entries if is_workspace_parent_entry(e)]
    nested = [e for e in entries if not is_workspace_parent_entry(e)]

    lines: list[str] = [
        "## notion_page_index_outline",
        "Source: persisted index from the last notion_refresh_page_index (same visibility as "
        "Notion search). This is not a live recursive crawl—only pages in that snapshot appear.",
        "",
        "### Workspace top-level pages",
        f"count={len(roots)} | parent.type=workspace — these are **siblings** at the workspace "
        "root in Notion, not “under” each other. A title like “Engineering …” here does **not** "
        "mean it lives inside “Corporate Engineering …” unless a nested row shows "
        "parent_page_id pointing at that corporate page. For “all docs under” a hub page, use "
        "notion_page_index_subtree after a **broad** refresh so children are in the index.",
    ]
    for e in sorted(roots, key=lambda x: x.title.lower()):
        lines.append(f"id={e.id} | title={e.title!r} | under=workspace")
        if len(lines) >= cap:
            lines.append("…truncated…")
            return "\n".join(lines)

    lines.extend(
        [
            "",
            "### Nested and non-workspace-root pages",
            f"count={len(nested)} | rows with parent.page_id show parent_title resolved from index "
            "when possible; use notion_list_pages_under_parent(parent_page_id=…) for children of "
            "a known anchor.",
        ]
    )

    def nested_sort_key(e: PageIndexEntry) -> tuple[str, str, str]:
        ppid = parent_page_id_from_entry(e)
        if ppid:
            pt = title_for_page_id(scope, ppid) or ""
            return (pt.lower(), e.title.lower(), e.id)
        p = e.parent if isinstance(e.parent, dict) else {}
        ptype = str(p.get("type", "unknown"))
        return (ptype, e.title.lower(), e.id)

    for e in sorted(nested, key=nested_sort_key):
        ppid = parent_page_id_from_entry(e)
        if ppid:
            pt = title_for_page_id(scope, ppid) or "(parent title not in index)"
            lines.append(
                f"id={e.id} | title={e.title!r} | parent_page_id={ppid} | parent_title={pt!r}"
            )
        else:
            p = e.parent if isinstance(e.parent, dict) else {}
            ptype = str(p.get("type", "unknown"))
            lines.append(f"id={e.id} | title={e.title!r} | parent_type={ptype}")
        if len(lines) >= cap:
            lines.append("…truncated…")
            break

    return "\n".join(lines)


def iter_entries_in_subtree(scope: UserScope, root_page_id: str) -> list[PageIndexEntry]:
    """Index entries whose ``parent.page_id`` chain (within this index) reaches ``root_page_id``.

    Excludes the root row itself. Pages not present in the index cannot be reached (narrow
    ``notion_refresh_page_index`` queries often omit deep children).
    """
    try:
        want = notion_client.normalize_notion_page_id(root_page_id)
    except ValueError:
        return []
    entries = list(load_index(scope).entries)
    by_id = {e.id: e for e in entries}

    def walks_up_to_root(start: PageIndexEntry) -> bool:
        seen: set[str] = set()
        cur: PageIndexEntry | None = start
        while cur is not None:
            pp = parent_page_id_from_entry(cur)
            if not pp:
                return False
            if pp == want:
                return True
            if pp in seen:
                return False
            seen.add(pp)
            cur = by_id.get(pp)
        return False

    out = [e for e in entries if e.id != want and walks_up_to_root(e)]
    out.sort(key=lambda x: x.title.lower())
    return out


def format_subtree_under_parent(
    scope: UserScope, root_page_id: str, *, max_lines: int = 120
) -> str:
    """List root + every index row whose parent chain reaches ``root_page_id`` (descendants only)."""
    cap = max(20, min(int(max_lines), 300))
    try:
        want = notion_client.normalize_notion_page_id(root_page_id)
    except ValueError:
        return "error=invalid_parent_page_id"
    entries = list(load_index(scope).entries)
    by_id = {e.id: e for e in entries}
    root_entry = by_id.get(want)
    descendants = iter_entries_in_subtree(scope, want)

    lines: list[str] = [
        "## notion_page_index_subtree",
        f"root_page_id={want}",
        "Only pages present in the **current** persisted index are listed (parent links walked "
        "inside that snapshot). If this list is short after a **narrow** refresh, run "
        "notion_refresh_page_index with query=\"\" and a higher max_pages so children are "
        "included, then call this tool again.",
        "",
    ]
    if root_entry:
        lines.append(f"root | id={root_entry.id} | title={root_entry.title!r}")
    else:
        lines.append(
            "root | (not in index — pass a page id that appears in notion_search_page_index / "
            "outline, or refresh broadly)"
        )
    lines.append("")
    lines.append(f"### Descendants in index ({len(descendants)})")
    if not descendants and not root_entry:
        lines.append(
            "empty | root not in index and no descendants | broaden refresh (query=\"\", "
            "max_pages=100) then retry"
        )
        return "\n".join(lines[:cap])
    for e in descendants:
        pp = parent_page_id_from_entry(e)
        pt = title_for_page_id(scope, pp) if pp else ""
        pl = f"parent_title={pt!r}" if pt else "parent_title=(unknown)"
        lines.append(f"id={e.id} | title={e.title!r} | parent_page_id={pp} | {pl}")
        if len(lines) >= cap:
            lines.append("…truncated…")
            break
    return "\n".join(lines)


def parent_page_id_from_entry(entry: PageIndexEntry) -> str | None:
    """Return normalized parent page id when ``entry.parent`` is a ``page_id`` parent."""
    return notion_client.parent_page_id_from_parent_dict(entry.parent)


def title_for_page_id(scope: UserScope, page_id: str) -> str:
    """Return title from index for ``page_id``, or empty string if unknown."""
    try:
        want = notion_client.normalize_notion_page_id(page_id)
    except ValueError:
        return ""
    for e in load_index(scope).entries:
        if e.id == want:
            return e.title
    return ""


def index_entry_for_page_id(scope: UserScope, page_id: str) -> PageIndexEntry | None:
    """Return the index row for ``page_id`` if present."""
    try:
        want = notion_client.normalize_notion_page_id(page_id)
    except ValueError:
        return None
    for e in load_index(scope).entries:
        if e.id == want:
            return e
    return None


def ancestor_chain_entries_bottom_up(scope: UserScope, page_id: str) -> list[PageIndexEntry]:
    """Walk ``parent.page_id`` links upward within the index (target → … → workspace-root page)."""
    try:
        want = notion_client.normalize_notion_page_id(page_id)
    except ValueError:
        return []
    by_id = {e.id: e for e in load_index(scope).entries}
    start = by_id.get(want)
    if not start:
        return []
    chain: list[PageIndexEntry] = [start]
    seen: set[str] = {start.id}
    while True:
        last = chain[-1]
        pp = parent_page_id_from_entry(last)
        if not pp:
            break
        if pp in seen:
            break
        parent_e = by_id.get(pp)
        if not parent_e:
            break
        seen.add(parent_e.id)
        chain.append(parent_e)
    return chain


def ancestor_titles_top_down(scope: UserScope, page_id: str) -> list[str]:
    """Titles from workspace-root hub down to this page (inclusive), using only the index graph."""
    ch = ancestor_chain_entries_bottom_up(scope, page_id)
    return [e.title or "(untitled)" for e in reversed(ch)]


def format_page_metadata_report(
    scope: UserScope,
    page_id: str,
    *,
    live_summary: dict[str, Any] | None = None,
) -> str:
    """Explain parent / hierarchy context; optional live API summary (no property values)."""
    try:
        want = notion_client.normalize_notion_page_id(page_id)
    except ValueError:
        return "error=invalid_page_id"
    lines: list[str] = ["## notion_page_metadata", f"page_id={want}", ""]
    entry = index_entry_for_page_id(scope, want)
    if entry:
        lines.extend(
            [
                "### Persisted index row",
                f"title={entry.title!r}",
                f"url={entry.url}",
                f"last_edited_time={entry.last_edited_time!r}",
                f"parent={json.dumps(entry.parent, sort_keys=True)}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Persisted index row",
                "(no row for this id in the current index — run notion_refresh_page_index)",
                "",
            ]
        )

    ac = ancestor_titles_top_down(scope, want)
    lines.extend(
        [
            "### Hierarchy (from index graph only)",
            "Workspace-root pages use parent.type=workspace in the API. The chain below is inferred "
            "only from parent_page_id links **between rows in this index**.",
            "",
        ]
    )
    if ac:
        lines.append("ancestor_titles_top_down=" + " > ".join(ac))
        hub = index_entry_for_page_id(scope, want)
        if hub and is_workspace_parent_entry(hub) and len(ac) == 1:
            lines.extend(
                [
                    "",
                    "interpretation=This page is a **workspace top-level** hub (not nested under "
                    "another page in Notion). Pages that share parent.type=workspace are **siblings** "
                    "in the same Notion workspace unless their index row shows parent_page_id "
                    "pointing at this hub. Use notion_page_index_subtree(parent_page_id=this id) "
                    "for descendants present in the index.",
                ]
            )
        elif len(ac) >= 2:
            lines.append(
                "interpretation=The leftmost title is the nearest workspace-root page in this "
                "index chain; pages under that hub have parent_page_id linking toward it."
            )
    else:
        lines.append("(cannot infer chain — id missing from index)")

    if live_summary:
        lines.extend(
            [
                "",
                "### Live Notion pages.retrieve (no property body values)",
                f"title_plain={live_summary.get('title_plain')!r}",
                f"url={live_summary.get('url')!r}",
                f"created_time={live_summary.get('created_time')!r}",
                f"last_edited_time={live_summary.get('last_edited_time')!r}",
                f"archived={live_summary.get('archived')!r}",
                f"in_trash={live_summary.get('in_trash')!r}",
                f"parent={json.dumps(live_summary.get('parent'), sort_keys=True)}",
                f"property_schema_keys={live_summary.get('property_schema_keys')!r}",
            ]
        )
    return "\n".join(lines)


def iter_page_ids_with_titles(scope: UserScope, page_ids: set[str]) -> list[tuple[str, str]]:
    """Each page id with best-effort title from the page index (stable sort by id)."""
    rows: list[tuple[str, str]] = []
    for pid in sorted(page_ids):
        title = title_for_page_id(scope, pid)
        if not title.strip():
            title = "(no title in index; run notion_refresh_page_index)"
        rows.append((pid, title))
    return rows


def iter_merged_draft_parents_with_titles(
    scope: UserScope, settings: Settings
) -> list[tuple[str, str]]:
    """Each merged draft parent id with best-effort title from the page index."""
    parents = notion_allowlist_store.merged_parent_ids(scope, settings)
    return iter_page_ids_with_titles(scope, parents)


def resolve_unique_page_id_by_title_hint(
    scope: UserScope, page_ids: set[str], hint: str, *, label: str
) -> tuple[str | None, str]:
    """Resolve a unique page id when ``hint`` matches part of its title (case-insensitive)."""
    raw = hint.strip().lower()
    if not raw:
        return None, "error=empty_title_hint"
    rows = iter_page_ids_with_titles(scope, page_ids)
    matches = [(pid, title) for pid, title in rows if raw in title.lower()]
    if len(matches) == 1:
        return matches[0][0], ""
    if not matches:
        lines = "\n".join(f"id={p} | title={t!r}" for p, t in rows)
        msg = (
            f"error=no_title_match | scope={label} | hint={hint!r} | "
            f"candidates:\n{lines or '(none)'}"
        )
        return None, msg
    lines = "\n".join(f"id={p} | title={t!r}" for p, t in matches)
    return None, f"error=ambiguous_title_hint | scope={label} | matches:\n{lines}"


def is_workspace_parent_entry(entry: PageIndexEntry) -> bool:
    """True when the Notion API marked this page's parent as the workspace root."""
    p = entry.parent
    return isinstance(p, dict) and p.get("type") == "workspace"


def bootstrap_draft_parent_candidates(
    scope: UserScope, *, title_needle: str = "", max_results: int = 15
) -> list[PageIndexEntry]:
    """Pages from the local index that can be offered as draft parents (integration-visible).

    Workspace-top-level pages sort first, then title. Filter by case-insensitive substring when
    ``title_needle`` is non-empty; otherwise take the first ``max_results`` rows after sort.
    """
    try:
        cap = int(max_results)
    except (TypeError, ValueError):
        cap = 15
    cap = max(1, min(cap, 50))
    needle = title_needle.strip().lower()
    rows = list(load_index(scope).entries)
    if needle:
        rows = [e for e in rows if needle in e.title.lower()]
    rows.sort(key=lambda e: (0 if is_workspace_parent_entry(e) else 1, e.title.lower()))
    return rows[:cap]


def list_index_children_of_parent(
    scope: UserScope,
    *,
    parent_id: str,
    title_needle: str = "",
    max_results: int = 50,
) -> list[PageIndexEntry]:
    """Index rows whose Notion parent is ``parent_id`` (direct children in the snapshot)."""
    try:
        want = notion_client.normalize_notion_page_id(parent_id)
    except ValueError:
        return []
    needle = title_needle.strip().lower()
    out: list[PageIndexEntry] = []
    for e in load_index(scope).entries:
        pp = parent_page_id_from_entry(e)
        if pp != want:
            continue
        if needle and needle not in e.title.lower():
            continue
        out.append(e)
        if len(out) >= max(1, min(max_results, 100)):
            break
    return out
