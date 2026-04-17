"""Tests for Neuuf coordinator CLI entrypoint."""

from __future__ import annotations

import sys

import pytest

from iso_agent.config import get_settings
from iso_agent.scripts import neuuf_coordinator_cli as cli


def test_neuuf_cli_one_shot_query(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return "OUT:" + q

    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    cli.main()
    assert "OUT:hello" in capsys.readouterr().out


def test_neuuf_cli_sets_tool_console_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") == "enabled"


def test_neuuf_cli_plain_console_skips_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgent:
        def __call__(self, q: str) -> str:
            return q

    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.delenv("STRANDS_TOOL_CONSOLE_MODE", raising=False)
    monkeypatch.setattr(cli, "create_neuuf_coordinator_agent", lambda _scope: _FakeAgent())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--plain-console", "--query", "x"])
    cli.main()
    assert cli.os.environ.get("STRANDS_TOOL_CONSOLE_MODE") is None


def test_neuuf_cli_exits_when_anthropic_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "anthropic")
    get_settings.cache_clear()
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ANTHROPIC_API_KEY" in err


def test_neuuf_cli_exits_when_bedrock_without_aws_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "bedrock")
    get_settings.cache_clear()

    class _SessionNoCreds:
        def get_credentials(self) -> None:
            return None

    monkeypatch.setattr(cli.boto3, "Session", lambda *a, **k: _SessionNoCreds())
    monkeypatch.setattr(sys, "argv", ["iso-neuuf-coordinator", "--query", "hello"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "AWS credentials" in err
