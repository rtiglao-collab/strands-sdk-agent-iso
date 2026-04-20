"""Tests for Notion fetch_page_text (nested blocks)."""

from __future__ import annotations

from typing import Any

from iso_agent.l3_runtime.integrations import notion_client


def test_fetch_page_summary_extracts_title_and_keys() -> None:
    class _Pages:
        def retrieve(self, **kwargs: Any) -> dict[str, Any]:
            page_id = kwargs.get("page_id", "")
            return {
                "id": page_id,
                "url": "https://notion.so/x",
                "parent": {"type": "workspace", "workspace": True},
                "created_time": "2026-01-01T00:00:00.000Z",
                "last_edited_time": "2026-01-02T00:00:00.000Z",
                "archived": False,
                "in_trash": False,
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Hub Title", "type": "text"}],
                    },
                    "Status": {"type": "select", "select": None},
                },
            }

    class _Client:
        pages = _Pages()

    pid = "11111111-1111-4111-8111-111111111111"
    s = notion_client.fetch_page_summary(_Client(), page_id=pid)
    assert s["title_plain"] == "Hub Title"
    assert "Status" in s["property_schema_keys"]
    assert s["parent"] == {"type": "workspace", "workspace": True}


def test_fetch_page_text_recurses_into_column_children() -> None:
    page = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    col = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

    class _Children:
        def list(self, **kwargs: Any) -> dict[str, Any]:
            bid = str(kwargs.get("block_id", ""))
            if bid.replace("-", "") == page.replace("-", ""):
                return {
                    "results": [
                        {
                            "object": "block",
                            "type": "column_list",
                            "id": col,
                            "has_children": True,
                            "column_list": {},
                        },
                    ],
                    "has_more": False,
                }
            if bid.replace("-", "") == col.replace("-", ""):
                return {
                    "results": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                            "has_children": False,
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "plain_text": "Text inside column"},
                                ],
                            },
                        },
                    ],
                    "has_more": False,
                }
            return {"results": [], "has_more": False}

    class _BlocksAPI:
        children = _Children()

    class _Client:
        blocks = _BlocksAPI()

    out = notion_client.fetch_page_text(_Client(), page_id=page, max_blocks=20, max_depth=4)
    assert "Text inside column" in out
