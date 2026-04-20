"""Tests for Notion QMS tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import memory_layout, notion_allowlist_store, notion_page_index_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client, notion_mcp
from iso_agent.l3_runtime.tools import notion_tools
from tests.notion_mcp_fakes import FakeNotionMcpClient


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))


def _tool_by_name(tools: list[Any], name: str) -> Any:
    for tool_obj in tools:
        if getattr(tool_obj, "tool_name", "") == name:
            return tool_obj
    names = [getattr(t, "tool_name", None) for t in tools]
    raise AssertionError(f"missing tool {name!r}, have {names}")


@pytest.fixture(autouse=True)
def _notion_test_isolation(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.delenv("ISO_AGENT_NOTION_TRANSPORT", raising=False)
    notion_mcp.reset_notion_mcp_for_tests()
    get_settings.cache_clear()
    yield
    notion_mcp.reset_notion_mcp_for_tests()


def _patch_mcp(monkeypatch: pytest.MonkeyPatch, fake: FakeNotionMcpClient) -> None:
    monkeypatch.setattr(notion_tools.notion_mcp, "ensure_notion_mcp_client", lambda _scope: fake)


def test_notion_tools_skipped_without_mcp_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Notion tools when hosted MCP client cannot start (no OAuth / transport off)."""
    monkeypatch.setattr(notion_tools.notion_mcp, "ensure_notion_mcp_client", lambda _scope: None)
    get_settings.cache_clear()
    assert notion_tools.build_notion_tools(_scope()) == []


def test_notion_tools_skipped_when_rest_only_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_TRANSPORT", "rest_only")
    monkeypatch.setattr(
        notion_tools.notion_mcp, "ensure_notion_mcp_client", lambda _scope: FakeNotionMcpClient()
    )
    get_settings.cache_clear()
    assert notion_tools.build_notion_tools(_scope()) == []


def test_notion_tools_skipped_when_explicitly_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ISO_AGENT_NOTION_ENABLED=false`` omits tools even when MCP is available."""
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    get_settings.cache_clear()
    assert notion_tools.build_notion_tools(_scope()) == []


def test_normalize_notion_page_id_accepts_compact_hex() -> None:
    dashed = "11111111-1111-4111-8111-111111111111"
    compact = dashed.replace("-", "")
    norm_d = notion_client.normalize_notion_page_id(dashed)
    norm_c = notion_client.normalize_notion_page_id(compact)
    assert norm_d == norm_c == notion_client.normalize_notion_page_id(dashed.lower())


def test_notion_refresh_page_index_clears_disk_when_search_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Stale index must be overwritten even when live search returns no pages."""
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    _patch_mcp(monkeypatch, FakeNotionMcpClient(search_hits=[]))
    get_settings.cache_clear()
    scope = UserScope.from_context(inbound_dm(user_id="refresh-empty", space="dm", thread="t"))
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "url": "https://notion.so/x",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Ghost", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    assert len(notion_page_index_store.load_index(scope).entries) == 1

    tools = notion_tools.build_notion_tools(scope)
    refresh = _tool_by_name(tools, "notion_refresh_page_index")
    out = str(refresh("", 50))
    assert "ok=index_cleared" in out
    assert "search_query_used=<(empty)>" in out
    assert len(notion_page_index_store.load_index(scope).entries) == 0


def test_notion_allowlist_add_draft_parent_by_choice_mocked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", raising=False)
    get_settings.cache_clear()
    scope = UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))
    pid = "11111111-1111-4111-8111-111111111111"
    _patch_mcp(monkeypatch, FakeNotionMcpClient(fetch_ok_ids={pid}))
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": pid,
                "url": "https://notion.so/p",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Engineering HQ", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    tools = notion_tools.build_notion_tools(scope)
    by_choice = _tool_by_name(tools, "notion_allowlist_add_draft_parent_by_choice")
    out = str(by_choice(1, "Engineering", 12))
    assert "ok=added_draft_parent" in out


def test_notion_create_qms_draft_for_parent_title_mocked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", parent)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    scope = UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": parent,
                "url": "https://notion.so/p",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Neuuf QMS Drafts", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    tools = notion_tools.build_notion_tools(scope)
    create_by_title = _tool_by_name(tools, "notion_create_qms_draft_for_parent_title")
    out = str(create_by_title("QMS Drafts", "from title", "body"))
    assert "22222222" in out


def test_notion_list_pages_under_parent_uses_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", parent)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    scope = UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": parent,
                "url": "https://notion.so/p",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Section Alpha", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": child,
                "url": "https://notion.so/c",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Nested Doc", "type": "text"}],
                    }
                },
                "parent": {"type": "page_id", "page_id": parent},
            },
        ],
    )
    tools = notion_tools.build_notion_tools(scope)
    lst = _tool_by_name(tools, "notion_list_pages_under_parent")
    out = str(lst(parent_title_substring="Alpha"))
    assert child in out
    assert "Nested" in out


def test_notion_create_draft_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", parent)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())

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
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", allowed)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    other = "33333333-3333-4333-8333-333333333333"
    out = str(read(other))
    assert "not_allowlisted" in out or "invalid" in out


def test_notion_read_accepts_hyphenless_allowlisted_id(monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", allowed)
    get_settings.cache_clear()
    _patch_mcp(
        monkeypatch,
        FakeNotionMcpClient(
            fetch_ok_ids={allowed},
            fetch_text_by_id={allowed: "body text"},
        ),
    )
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111111141118111111111111111"))
    assert out == "body text"


def test_notion_tools_registers_read_create_when_allowlists_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """MCP + OAuth suffices; allowlists can be filled later via file or env."""
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", raising=False)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    tools = notion_tools.build_notion_tools(_scope())
    names = {getattr(t, "tool_name", "") for t in tools}
    assert "notion_read_page" in names
    assert "notion_create_qms_draft" in names
    assert "notion_create_qms_draft_for_parent_title" in names
    assert "notion_list_draft_parents" in names
    assert "notion_list_pages_under_parent" in names
    assert "notion_allowlist_list" in names
    assert "notion_allowlist_add_read_page" in names
    assert "notion_bootstrap_draft_parent_choices" in names
    assert "notion_allowlist_add_draft_parent_by_choice" in names
    assert "notion_discover_connected_pages" not in names


def test_notion_read_uses_persisted_allowlist_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    get_settings.cache_clear()

    scope = _scope()
    notion_allowlist_store.save_persisted_allowlist(scope, {allowed}, set())

    _patch_mcp(
        monkeypatch,
        FakeNotionMcpClient(
            fetch_ok_ids={allowed},
            fetch_text_by_id={allowed: "from file allowlist"},
        ),
    )
    tools = notion_tools.build_notion_tools(scope)
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111111141118111111111111111"))
    assert out == "from file allowlist"


def test_notion_allowlist_add_read_page_requires_access(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "55555555-5555-4555-8555-555555555555"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient(fetch_ok_ids=set()))
    tools = notion_tools.build_notion_tools(_scope())
    add = _tool_by_name(tools, "notion_allowlist_add_read_page")
    out = str(add(page))
    assert "not_accessible" in out
    assert "notion-fetch" in out


def test_notion_read_empty_merged_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", raising=False)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
    tools = notion_tools.build_notion_tools(_scope())
    read = _tool_by_name(tools, "notion_read_page")
    out = str(read("11111111-1111-4111-8111-111111111111"))
    assert "no_read_allowlist" in out


def test_notion_create_empty_merged_parents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    monkeypatch.delenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", raising=False)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient())
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


def test_notion_discover_empty_warns_when_disk_index_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "true")
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient(search_hits=[]))
    scope = UserScope.from_context(inbound_dm(user_id="stale-idx", space="dm", thread="t"))
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "url": "https://notion.so/x",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Ghost", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    tools = notion_tools.build_notion_tools(scope)
    discover = _tool_by_name(tools, "notion_discover_connected_pages")
    out = str(discover("", 10))
    assert "stale_disk_index" in out
    assert "notion_refresh_page_index" in out


def test_notion_discover_connected_pages_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "true")
    get_settings.cache_clear()
    hits = [
        {
            "object": "page",
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
    _patch_mcp(monkeypatch, FakeNotionMcpClient(search_hits=hits))

    tools = notion_tools.build_notion_tools(_scope())
    discover = _tool_by_name(tools, "notion_discover_connected_pages")
    out = str(discover("", 10))
    assert "aaaaaaaa" in out
    assert "Gap doc" in out


def test_notion_refresh_and_search_page_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "false")
    get_settings.cache_clear()
    hits = [
        {
            "object": "page",
            "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "url": "https://notion.so/b",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Engineering Hub", "type": "text"}],
                }
            },
            "parent": {"type": "workspace", "workspace": True},
        }
    ]
    _patch_mcp(monkeypatch, FakeNotionMcpClient(search_hits=hits))

    scope = _scope()
    tools = notion_tools.build_notion_tools(scope)
    refresh = _tool_by_name(tools, "notion_refresh_page_index")
    search = _tool_by_name(tools, "notion_search_page_index")
    r1 = str(refresh("", 10))
    assert "ok=index_refreshed" in r1
    assert "search_query_used=<(empty)>" in r1
    r2 = str(search("Engineering", 10))
    assert "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" in r2
    assert "Engineering Hub" in r2
    outline = _tool_by_name(tools, "notion_page_index_outline")
    r3 = str(outline(80))
    assert "Workspace top-level" in r3
    assert "Engineering Hub" in r3
    subtree = _tool_by_name(tools, "notion_page_index_subtree")
    r4 = str(subtree("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", 80))
    assert "## notion_page_index_subtree" in r4
    assert "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" in r4
    assert "Engineering Hub" in r4
    meta = _tool_by_name(tools, "notion_page_metadata")
    r5 = str(meta("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", False))
    assert "## notion_page_metadata" in r5
    assert "Engineering Hub" in r5


def test_notion_discovery_on_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", raising=False)
    get_settings.cache_clear()
    _patch_mcp(monkeypatch, FakeNotionMcpClient(search_hits=[]))
    tools = notion_tools.build_notion_tools(_scope())
    _tool_by_name(tools, "notion_discover_connected_pages")
