"""Tests for Neuuf coordinator CLI entrypoint."""

from __future__ import annotations

import sys

import pytest
from strands.handlers.callback_handler import PrintingCallbackHandler

from iso_agent.scripts import neuuf_coordinator_cli as cli


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

