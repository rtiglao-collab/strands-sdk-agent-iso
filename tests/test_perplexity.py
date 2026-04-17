"""Tests for Perplexity MCP integration (no real Docker)."""

import pytest

from iso_agent.config import Settings, get_settings
from iso_agent.l3_runtime.integrations import perplexity


@pytest.fixture(autouse=True)
def _reset_perplexity_singleton() -> None:
    perplexity.reset_perplexity_mcp_for_tests()
    yield
    perplexity.reset_perplexity_mcp_for_tests()


def test_perplexity_not_configured_without_key(monkeypatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("ISO_AGENT_PERPLEXITY_TRANSPORT", "docker")
    get_settings.cache_clear()
    assert perplexity.perplexity_mcp_configured() is False
    assert perplexity.get_perplexity_mcp_tools() is None


def test_perplexity_disabled_transport(monkeypatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    monkeypatch.setenv("ISO_AGENT_PERPLEXITY_TRANSPORT", "disabled")
    get_settings.cache_clear()
    assert perplexity.perplexity_mcp_configured() is False


def test_get_tools_with_fake_client(monkeypatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    monkeypatch.setenv("ISO_AGENT_PERPLEXITY_TRANSPORT", "docker")
    get_settings.cache_clear()

    class _FakeClient:
        def __init__(self, _factory: object) -> None:
            del _factory

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def list_tools_sync(self) -> list[object]:
            return []

    monkeypatch.setattr(perplexity, "MCPClient", _FakeClient)
    tools = perplexity.get_perplexity_mcp_tools()
    assert tools == []


def test_settings_default_transport() -> None:
    get_settings.cache_clear()
    assert Settings().perplexity_transport == "disabled"
