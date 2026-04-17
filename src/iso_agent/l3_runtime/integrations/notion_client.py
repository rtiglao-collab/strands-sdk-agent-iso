"""Notion API helpers (integration token, pages + blocks).

Token: read ``NOTION_TOKEN`` from the environment (Notion internal integration secret).
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
    def pages(self) -> Any: ...

    def blocks(self) -> Any: ...

    def search(self, **kwargs: Any) -> Any: ...


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
        client.pages().create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties=props,
            children=children,
        ),
    )


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


def fetch_page_text(client: _NotionClient, *, page_id: str, max_blocks: int = 50) -> str:
    """Return plain text extracted from top-level blocks (paragraphs and headings)."""
    parts: list[str] = []
    cursor: str | None = None
    count = 0
    page_id = normalize_notion_page_id(page_id)
    while count < max_blocks:
        kwargs: dict[str, Any] = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.blocks().children.list(**kwargs)
        for block in resp.get("results", []):
            count += 1
            if count > max_blocks:
                break
            btype = block.get("type", "")
            payload = block.get(btype, {})
            rich = payload.get("rich_text", [])
            for rt in rich:
                if rt.get("type") == "text":
                    parts.append(str(rt.get("plain_text", "")))
        cursor = resp.get("next_cursor")
        if not resp.get("has_more") or not cursor:
            break
    return "\n".join(p for p in parts if p).strip()
