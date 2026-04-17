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


def is_valid_notion_id(value: str) -> bool:
    """Return True if ``value`` looks like a Notion UUID."""
    return bool(_UUID_RE.match(value.strip()))


class _NotionClient(Protocol):
    def pages(self) -> Any: ...

    def blocks(self) -> Any: ...


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


def fetch_page_text(client: _NotionClient, *, page_id: str, max_blocks: int = 50) -> str:
    """Return plain text extracted from top-level blocks (paragraphs and headings)."""
    parts: list[str] = []
    cursor: str | None = None
    count = 0
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
