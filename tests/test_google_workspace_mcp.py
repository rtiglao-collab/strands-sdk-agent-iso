"""Tests for Google Workspace MCP integration (no real npx)."""

from __future__ import annotations

import pytest
from strands_tools import calculator

from iso_agent.config import Settings, get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import google_workspace_mcp
from iso_agent.l3_runtime.team import coordinator as coord
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="gwmcp-test", space="dm", thread="t"))


@pytest.fixture(autouse=True)
def _reset_google_workspace_mcp() -> None:
    google_workspace_mcp.reset_google_workspace_mcp_for_tests()
    yield
    google_workspace_mcp.reset_google_workspace_mcp_for_tests()
    get_settings.cache_clear()


def test_google_workspace_mcp_disabled_by_default() -> None:
    get_settings.cache_clear()
    assert google_workspace_mcp.google_workspace_mcp_configured() is False
    assert google_workspace_mcp.get_google_workspace_mcp_tools() is None


def test_google_workspace_mcp_stdio_without_npx_never_crashes_import() -> None:
    """Startup may fail at runtime; this test only checks disabled path."""
    get_settings.cache_clear()
    assert Settings().google_workspace_mcp_transport == "disabled"


def test_get_tools_with_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT", "stdio")
    get_settings.cache_clear()

    class _FakeClient:
        def __init__(self, _factory: object, **_kwargs: object) -> None:
            del _factory

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def list_tools_sync(self) -> list[object]:
            return []

    monkeypatch.setattr(google_workspace_mcp, "MCPClient", _FakeClient)
    tools = google_workspace_mcp.get_google_workspace_mcp_tools()
    assert tools == []


def test_coordinator_merges_google_workspace_mcp_tool_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coord, "get_google_workspace_mcp_tools", lambda: [calculator])
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "calculator" in agent.tool_names


def test_coordinator_has_no_legacy_drive_tool_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neuuf coordinator must not expose removed REST Drive tool names."""

    monkeypatch.setattr(coord, "get_google_workspace_mcp_tools", lambda: [calculator])

    monkeypatch.setenv("ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT", "stdio")
    get_settings.cache_clear()
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "calculator" in agent.tool_names
    assert "drive_list_folder" not in agent.tool_names

    monkeypatch.setenv("ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT", "disabled")
    get_settings.cache_clear()
    agent2 = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "drive_list_folder" not in agent2.tool_names
