"""Tests for Neuuf coordinator CLI entrypoint."""

from __future__ import annotations

import sys

import pytest

from iso_agent.scripts import neuuf_coordinator_cli as cli


def test_neuuf_cli_one_shot_query(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return "OUT:" + q

    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    cli.main()
    assert "OUT:hello" in capsys.readouterr().out


def test_neuuf_cli_sets_tool_console_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") == "enabled"


def test_neuuf_cli_plain_console_skips_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--plain-console", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") is None
