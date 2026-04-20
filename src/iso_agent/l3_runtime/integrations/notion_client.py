"""Notion REST API helpers (pages + blocks) for manual / legacy callers.

Coordinator ``notion_*`` tools use hosted Notion MCP instead; this module still
reads ``NOTION_TOKEN`` when REST helpers are invoked (e.g. ``tests/manual_notion_page_inspect.py``).
"""

from __future__ import annotations

import re
from typing import Any, Protocol, cast

_NOTION_VERSION = "2022-06-28"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


def normalize_notion_page_id(value: str) -> str:
    """Return canonical hyphenated lowercase UUID for a Notion page/database id segment."""
    raw = value.strip()
    if _UUID_RE.match(raw):
        return raw.lower()
    compact = raw.replace("-", "")
    if not _HEX32_RE.match(compact):
        msg = "invalid notion page id format"
        raise ValueError(msg)
    c = compact.lower()
    return f"{c[0:8]}-{c[8:12]}-{c[12:16]}-{c[16:20]}-{c[20:32]}"


def is_valid_notion_id(value: str) -> bool:
    """Return True if ``value`` is a Notion UUID (with or without hyphens)."""
    try:
        normalize_notion_page_id(value)
        return True
    except ValueError:
        return False


class _NotionClient(Protocol):
    """Shape of ``notion_client.Client`` (``pages`` / ``blocks`` are endpoint objects, not calls)."""

    pages: Any
    blocks: Any

    def search(self, **kwargs: Any) -> Any: ...


def page_retrieve_diagnostic(client: _NotionClient, *, page_id: str) -> tuple[bool, str]:
    """Try ``pages.retrieve``; return ``(True, "")`` or ``(False, short_reason)`` (no secrets)."""
    pid = normalize_notion_page_id(page_id)
    try:
        client.pages.retrieve(page_id=pid)
    except Exception as exc:
        tag = type(exc).__name__
        code = getattr(exc, "code", None)
        status = getattr(exc, "status", None)
        if code is not None:
            return False, f"{tag}(code={code})"
        if status is not None:
            return False, f"{tag}(status={status})"
        return False, tag
    return True, ""


def page_exists(client: _NotionClient, *, page_id: str) -> bool:
    """Return True if Notion returns a page for ``page_id`` (integration must have access)."""
    ok, _ = page_retrieve_diagnostic(client, page_id=page_id)
    return ok


def fetch_page_summary(client: _NotionClient, *, page_id: str) -> dict[str, Any]:
    """Return a small, log-safe dict from ``pages.retrieve`` (no rich property payloads)."""
    pid = normalize_notion_page_id(page_id)
    raw = cast(dict[str, Any], client.pages.retrieve(page_id=pid))
    props = raw.get("properties") or {}
    keys: list[str] = []
    if isinstance(props, dict):
        keys = sorted(props.keys())
    return {
        "id": str(raw.get("id", "")),
        "url": str(raw.get("url", "")),
        "parent": raw.get("parent"),
        "created_time": raw.get("created_time"),
        "last_edited_time": raw.get("last_edited_time"),
        "archived": raw.get("archived"),
        "in_trash": raw.get("in_trash"),
        "title_plain": page_plain_title(raw),
        "property_schema_keys": keys,
    }


def build_notion_client(token: str) -> _NotionClient:
    """Return a configured Notion SDK client."""
    from notion_client import Client

    return cast(_NotionClient, Client(auth=token, notion_version=_NOTION_VERSION))


def _paragraph_blocks(body: str, *, max_chunk: int = 1800) -> list[dict[str, Any]]:
    text = body.strip() or " "
    chunks: list[str] = []
    for i in range(0, len(text), max_chunk):
        chunks.append(text[i : i + max_chunk])
    blocks: list[dict[str, Any]] = []
    for chunk in chunks[: 99]:  # stay under API block limits per request
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                },
            }
        )
    return blocks


def create_child_page(
    client: _NotionClient,
    *,
    parent_page_id: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    """Create a child page under ``parent_page_id`` with title and paragraph body."""
    parent_page_id = normalize_notion_page_id(parent_page_id)
    props = {
        "title": {
            "title": [{"type": "text", "text": {"content": title[:2000]}}],
        }
    }
    children = _paragraph_blocks(body)
    return cast(
        dict[str, Any],
        client.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties=props,
            children=children,
        ),
    )


def parent_page_id_from_parent_dict(parent: dict[str, Any]) -> str | None:
    """Return normalized parent page id when ``parent`` is Notion's ``page_id`` block."""
    if not isinstance(parent, dict):
        return None
    if parent.get("type") != "page_id":
        return None
    raw = parent.get("page_id")
    if not raw:
        return None
    try:
        return normalize_notion_page_id(str(raw))
    except ValueError:
        return None


def page_plain_title(page: dict[str, Any]) -> str:
    """Best-effort title from a Notion page object (search or retrieve)."""
    props = page.get("properties") or {}
    for prop in props.values():
        if not isinstance(prop, dict):
            continue
        if prop.get("type") != "title":
            continue
        parts = prop.get("title") or []
        return "".join(str(t.get("plain_text", "")) for t in parts if isinstance(t, dict))
    return ""


def search_connected_pages(
    client: _NotionClient,
    *,
    query: str = "",
    page_size: int = 25,
) -> list[dict[str, Any]]:
    """Return page objects the integration can access (``POST /v1/search``)."""
    page_size = max(1, min(page_size, 100))
    payload: dict[str, Any] = {
        "page_size": page_size,
        "filter": {"value": "page", "property": "object"},
    }
    if query.strip():
        payload["query"] = query.strip()
    resp = client.search(**payload)
    if not isinstance(resp, dict):
        return []
    raw = resp.get("results", [])
    return [cast(dict[str, Any], item) for item in raw if isinstance(item, dict)]


def fetch_page_text(
    client: _NotionClient,
    *,
    page_id: str,
    max_blocks: int = 50,
    max_depth: int = 3,
) -> str:
    """Return plain text from page blocks, recursing into children (columns, toggles, etc.).

    ``max_blocks`` caps total **blocks enumerated** across the tree; ``max_depth`` limits nesting
    depth from the page root (0 = direct children only).
    """
    parts: list[str] = []
    page_id = normalize_notion_page_id(page_id)
    seen = 0

    def _append_rich(payload: dict[str, Any]) -> None:
        for rt in payload.get("rich_text", []) or []:
            if isinstance(rt, dict) and rt.get("type") == "text":
                t = str(rt.get("plain_text", ""))
                if t:
                    parts.append(t)

    def walk(block_id: str, depth: int) -> None:
        nonlocal seen
        if depth > max_depth or seen >= max_blocks:
            return
        cursor: str | None = None
        while seen < max_blocks:
            kwargs: dict[str, Any] = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = client.blocks.children.list(**kwargs)
            for block in resp.get("results", []):
                if seen >= max_blocks:
                    break
                seen += 1
                btype = str(block.get("type", ""))
                payload = block.get(btype, {}) if btype else {}
                if isinstance(payload, dict):
                    _append_rich(payload)
                bid = block.get("id")
                if (
                    depth < max_depth
                    and seen < max_blocks
                    and block.get("has_children")
                    and bid
                ):
                    walk(str(bid), depth + 1)
            cursor = resp.get("next_cursor")
            if not resp.get("has_more") or not cursor:
                break

    walk(page_id, 0)
    return "\n".join(p for p in parts if p).strip()
