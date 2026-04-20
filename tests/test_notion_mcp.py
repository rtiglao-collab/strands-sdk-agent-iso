"""Tests for Notion hosted MCP integration (no live Notion calls)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from strands_tools import calculator

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import memory_layout
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_mcp
from iso_agent.l3_runtime.team import coordinator as coord
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator
from iso_agent.l3_runtime.tools import notion_tools
from tests.notion_mcp_fakes import FakeNotionMcpClient


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="notion-mcp-test", space="dm", thread="t"))


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    yield
    get_settings.cache_clear()


def test_get_notion_mcp_tools_none_when_rest_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_TRANSPORT", "rest_only")
    get_settings.cache_clear()
    assert notion_mcp.get_notion_mcp_tools(_scope()) is None


def test_coordinator_merges_mcp_tool_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coord, "get_notion_mcp_tools", lambda _scope: [calculator])
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "calculator" in agent.tool_names


def test_mcp_primary_still_registers_discovery_when_mcp_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ISO_AGENT_NOTION_TRANSPORT", "mcp_primary")
    monkeypatch.setenv("ISO_AGENT_NOTION_DISCOVERY_ENABLED", "true")
    get_settings.cache_clear()
    scope = UserScope.from_context(inbound_dm(user_id="nd", space="dm", thread="t"))
    monkeypatch.setattr(
        notion_tools.notion_mcp, "ensure_notion_mcp_client", lambda _s: FakeNotionMcpClient()
    )
    tools = notion_tools.build_notion_tools(scope)
    names = [getattr(t, "tool_name", "") for t in tools]
    assert "notion_discover_connected_pages" in names


def test_reset_notion_mcp_for_tests_closes_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Fake:
        exited = False

        def __init__(self, *_a: object, **_kw: object) -> None:
            pass

        def __enter__(self) -> _Fake:
            return self

        def __exit__(self, *_a: object) -> None:
            _Fake.exited = True

        def list_tools_sync(self) -> list[object]:
            return []

    _Fake.exited = False
    monkeypatch.setenv("ISO_AGENT_NOTION_TRANSPORT", "hybrid")
    get_settings.cache_clear()
    scope = _scope()
    store = scope.memory_root / "notion" / "mcp_oauth.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        '{"access_token":"a","refresh_token":"r","expires_at":9999999999,'
        '"client_id":"c","token_endpoint":"https://example.invalid/token"}',
        encoding="utf-8",
    )
    notion_mcp.reset_notion_mcp_for_tests()
    monkeypatch.setattr(notion_mcp, "MCPClient", _Fake)
    notion_mcp.get_notion_mcp_tools(scope)
    notion_mcp.reset_notion_mcp_for_tests()
    assert _Fake.exited is True


def test_notion_mcp_oauth_tool_when_repl_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_TRANSPORT", "hybrid")
    get_settings.cache_clear()
    agent = build_neuuf_coordinator(
        _scope(), include_coding_tools=False, include_notion_mcp_oauth_tool=True
    )
    assert "notion_mcp_oauth_interactive_login" in agent.tool_names


def test_notion_mcp_oauth_tool_off_by_default() -> None:
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "notion_mcp_oauth_interactive_login" not in agent.tool_names


def test_ensure_fresh_oauth_bootstraps_missing_expires_at(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    notion_mcp.reset_notion_mcp_for_tests()
    scope = UserScope.from_context(inbound_dm(user_id="exp-missing", space="dm", thread="t"))
    path = notion_mcp.notion_mcp_oauth_store_path(scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"access_token":"tok","refresh_token":"r","client_id":"c","token_endpoint":"https://x/t"}',
        encoding="utf-8",
    )
    before = time.time()
    out = notion_mcp.ensure_fresh_oauth_store(scope)
    assert out is not None
    assert out["access_token"] == "tok"
    data = json.loads(path.read_text(encoding="utf-8"))
    exp = data.get("expires_at")
    assert isinstance(exp, (int, float))
    assert float(exp) >= before + 3500


def test_ensure_fresh_oauth_keeps_stale_token_when_refresh_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    notion_mcp.reset_notion_mcp_for_tests()
    scope = UserScope.from_context(inbound_dm(user_id="refresh-fail", space="dm", thread="t"))
    path = notion_mcp.notion_mcp_oauth_store_path(scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": "stale-access",
                "refresh_token": "r",
                "client_id": "c",
                "token_endpoint": "https://x/token",
                "expires_at": 1.0,
            }
        ),
        encoding="utf-8",
    )

    def _boom(*_a: object, **_kw: object) -> dict[str, object]:
        raise RuntimeError("network")

    monkeypatch.setattr(notion_mcp, "_refresh_store_sync", _boom)
    out = notion_mcp.ensure_fresh_oauth_store(scope)
    assert out is not None
    assert out["access_token"] == "stale-access"
