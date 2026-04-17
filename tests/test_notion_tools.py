"""Tests for Notion QMS tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import memory_layout, notion_allowlist_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client
from iso_agent.l3_runtime.tools import notion_tools


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))


def _tool_by_name(tools: list[Any], name: str) -> Any:
    for tool_obj in tools:
        if getattr(tool_obj, "tool_name", "") == name:
            return tool_obj
    names = [getattr(t, "tool_name", None) for t in tools]
    raise AssertionError(f"missing tool {name!r}, have {names}")


def test_notion_tools_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Must not inherit Notion flags or ``NOTION_TOKEN`` from the developer shell."""
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    get_settings.cache_clear()
    assert notion_tools.build_notion_tools(_scope()) == []


def test_normalize_notion_page_id_accepts_compact_hex() -> None:
    dashed = "11111111-1111-4111-8111-111111111111"
    compact = dashed.replace("-", "")
    norm_d = notion_client.normalize_notion_page_id(dashed)
    norm_c = notion_client.normalize_notion_page_id(compact)
    assert norm_d == norm_c == notion_client.normalize_notion_page_id(dashed.lower())


def test_notion_create_draft_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", parent)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )

    def _fake_create(_client: object, *, parent_page_id: str, title: str, body: str) -> dict:
        del _client, body
        assert parent_page_id == parent
        assert title.startswith("[DRAFT]")
        return {"id": "22222222-2222-4222-8222-222222222222", "url": "https://notion.so/x"}

    monkeypatch.setattr(notion_tools.notion_client, "create_child_page", _fake_create)

    tools = notion_tools.build_notion_tools(_scope())
    create = _tool_by_name(tools, "notion_create_qms_draft")
    out = str(
        create(
            "11111111111141118111111111111111",
            "Gap follow-up",
            "Details here.",
            "https://drive.google.com/file/d/abc",
        )
    )
    assert "22222222" in out
    assert "url=" in out


def test_notion_read_rejects_unknown_page(monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", allowed)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    other = "33333333-3333-4333-8333-333333333333"
    out = str(read(other))
    assert "not_allowlisted" in out or "invalid" in out


def test_notion_read_accepts_hyphenless_allowlisted_id(monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", allowed)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )

    def _fake_fetch(_client: object, *, page_id: str, max_blocks: int = 50) -> str:
        del _client, max_blocks
        assert page_id == allowed
        return "body text"

    monkeypatch.setattr(notion_tools.notion_client, "fetch_page_text", _fake_fetch)
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111111141118111111111111111"))
    assert out == "body text"


def test_notion_tools_registers_read_create_when_allowlists_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Token + client suffices; allowlists can be filled later via persisted file or env."""
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", raising=False)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    tools = notion_tools.build_notion_tools(_scope())
    names = {getattr(t, "tool_name", "") for t in tools}
    assert "notion_read_page" in names
    assert "notion_create_qms_draft" in names
    assert "notion_allowlist_list" in names
    assert "notion_allowlist_add_read_page" in names
    assert "notion_discover_connected_pages" not in names


def test_notion_read_uses_persisted_allowlist_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    get_settings.cache_clear()

    scope = _scope()
    notion_allowlist_store.save_persisted_allowlist(scope, {allowed}, set())

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )

    def _fake_fetch(_client: object, *, page_id: str, max_blocks: int = 50) -> str:
        del _client, max_blocks
        assert page_id == allowed
        return "from file allowlist"

    monkeypatch.setattr(notion_tools.notion_client, "fetch_page_text", _fake_fetch)
    tools = notion_tools.build_notion_tools(scope)
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111111141118111111111111111"))
    assert out == "from file allowlist"


def test_notion_allowlist_add_read_page_requires_access(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "55555555-5555-4555-8555-555555555555"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    get_settings.cache_clear()
    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    monkeypatch.setattr(notion_tools.notion_client, "page_exists", lambda _c, *, page_id: False)
    tools = notion_tools.build_notion_tools(_scope())
    add = _tool_by_name(tools, "notion_allowlist_add_read_page")
    out = str(add(page))
    assert "not_accessible" in out


def test_notion_read_empty_merged_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111-1111-4111-8111-111111111111"))
    assert "no_read_allowlist" in out


def test_notion_create_empty_merged_parents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    tools = notion_tools.build_notion_tools(_scope())
    create = _tool_by_name(tools, "notion_create_qms_draft")
    out = str(
        create(
            "11111111-1111-4111-8111-111111111111",
            "t",
            "b",
        )
    )
    assert "no_draft_parent_allowlist" in out


def test_notion_discover_connected_pages_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "true")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )

    def _fake_search(
        _client: object,
        *,
        query: str = "",
        page_size: int = 25,
    ) -> list[dict]:
        del _client, query, page_size
        return [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "url": "https://notion.so/a",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Gap doc", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            }
        ]

    monkeypatch.setattr(notion_tools.notion_client, "search_connected_pages", _fake_search)

    tools = notion_tools.build_notion_tools(_scope())
    discover = _tool_by_name(tools, "notion_discover_connected_pages")
    out = str(discover("", 10))
    assert "aaaaaaaa" in out
    assert "Gap doc" in out
