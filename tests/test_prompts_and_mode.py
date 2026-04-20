"""Tests for role prompts and primary agent mode."""

import iso_agent.l1_router.handler as handler_mod
from iso_agent.config import Settings, get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l1_router.handler import handle_user_message
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.prompts import load_role_prompt


def test_load_role_prompt_researcher() -> None:
    text = load_role_prompt("researcher")
    assert "research" in text.lower()


def test_neuuf_coordinator_prompt_mandates_natural_language_notion_flow() -> None:
    text = load_role_prompt("neuuf_coordinator")
    assert "natural-language notion creates" in text.lower()
    assert "notion_bootstrap_draft_parent_choices" in text
    assert "confirm-before-write" in text.lower()
    assert "tool not found in registry" in text.lower()
    assert "spreadsheet" in text.lower()
    assert "file type first" in text.lower()
    assert "iso_agent_google_workspace_mcp_debug" in text.lower().replace("-", "_")


def test_primary_mode_demo_default() -> None:
    get_settings.cache_clear()
    s = Settings()
    assert s.primary_mode == "demo"


def test_primary_mode_neuuf_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ISO_AGENT_PRIMARY_MODE", "neuuf")
    get_settings.cache_clear()
    s = Settings()
    assert s.primary_mode == "neuuf"


def test_handler_routes_neuuf(monkeypatch) -> None:
    monkeypatch.setenv("ISO_AGENT_PRIMARY_MODE", "neuuf")
    get_settings.cache_clear()

    class _FakeAgent:
        def __call__(self, text: str) -> str:
            del text
            return "neuuf-branch"

    monkeypatch.setattr(
        handler_mod,
        "create_neuuf_coordinator_agent",
        lambda scope: _FakeAgent(),
    )
    ctx = inbound_dm(user_id="u", space="dm", thread="t")
    scope = UserScope.from_context(ctx)
    assert handle_user_message(scope, "hi") == "neuuf-branch"
    monkeypatch.delenv("ISO_AGENT_PRIMARY_MODE", raising=False)
    get_settings.cache_clear()
