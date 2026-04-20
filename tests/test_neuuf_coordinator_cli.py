"""Tests for Neuuf coordinator CLI entrypoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from strands.handlers.callback_handler import PrintingCallbackHandler

from iso_agent.config import Settings, get_settings
from iso_agent.l3_runtime.cli import RichAgentConsoleCallback
from iso_agent.scripts import neuuf_coordinator_cli as cli


@pytest.fixture(autouse=True)
def _neuuf_cli_reset_google_workspace_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT", raising=False)
    monkeypatch.delenv("ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG", raising=False)
    get_settings.cache_clear()
    yield
    # ``main()`` assigns these via ``os.environ``; pop so other test modules see a clean env.
    os.environ.pop("ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT", None)
    os.environ.pop("ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG", None)
    get_settings.cache_clear()


def test_print_agent_result_skips_rich_callback(capsys: pytest.CaptureFixture[str]) -> None:
    class _Agent:
        callback_handler = RichAgentConsoleCallback()

    cli._print_agent_result(_Agent(), "duplicate")
    assert "duplicate" not in capsys.readouterr().out


def test_neuuf_cli_google_workspace_defaults_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    cli._apply_neuuf_cli_google_workspace_defaults()
    assert os.environ["ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT"] == "stdio"
    assert os.environ["ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG"] == "true"


def test_neuuf_cli_google_workspace_defaults_skip_when_dotenv_sets_transport(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=disabled\n", encoding="utf-8"
    )
    cli._apply_neuuf_cli_google_workspace_defaults()
    assert "ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT" not in os.environ
    assert Settings().google_workspace_mcp_transport == "disabled"


def test_neuuf_cli_one_shot_query(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return "OUT:" + q

    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _FakeAgent(),
    )
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    cli.main()
    assert "OUT:hello" in capsys.readouterr().out


def test_neuuf_cli_one_shot_skips_duplicate_final_print_with_streaming_callback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _StreamingAgent:
        callback_handler = PrintingCallbackHandler()

        def __call__(self, q: str) -> str:
            return "SHOULD_NOT_PRINT_TWICE:" + q

    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _StreamingAgent(),
    )
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    cli.main()
    out = capsys.readouterr().out
    assert "SHOULD_NOT_PRINT_TWICE" not in out


def test_neuuf_cli_sets_tool_console_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _FakeAgent(),
    )
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") == "enabled"


def test_neuuf_cli_sets_bypass_tool_consent_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.delenv("BYPASS_TOOL_CONSENT", raising=False)
    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _FakeAgent(),
    )
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("BYPASS_TOOL_CONSENT") == "true"
    capsys.readouterr()


def test_neuuf_cli_require_tool_consent_disables_bypass(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _FakeAgent(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["iso-neuuf-coordinator", "--require-tool-consent", "--query", "x"],
    )
    cli.main()
    assert cli.os.environ.get("BYPASS_TOOL_CONSENT") == "false"
    capsys.readouterr()


def test_neuuf_cli_plain_console_skips_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(
        cli,
        "create_neuuf_coordinator_agent",
        lambda _scope, **_kw: _FakeAgent(),
    )
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--plain-console", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") is None

def test_neuuf_cli_notion_mcp_login_runs_login_and_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    def _fake_login(scope, *, open_browser: bool = True) -> None:
        del open_browser
        called.append(scope.user_key)

    monkeypatch.setattr(
        "iso_agent.l3_runtime.integrations.notion_mcp.run_notion_mcp_interactive_login",
        _fake_login,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["iso-neuuf-coordinator", "--notion-mcp-login", "--notion-mcp-login-user-id", "u1"],
    )
    cli.main()
    assert called and called[0]
