"""Tests for Notion QMS tools."""

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.tools import notion_tools


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))


def test_notion_tools_disabled_by_default() -> None:
    get_settings.cache_clear()
    assert notion_tools.build_notion_tools(_scope()) == []


def test_notion_create_draft_mocked(monkeypatch) -> None:
    parent = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", parent)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )

    def _fake_create(_client, *, parent_page_id: str, title: str, body: str) -> dict:
        del body
        return {"id": "22222222-2222-4222-8222-222222222222", "url": "https://notion.so/x"}

    monkeypatch.setattr(notion_tools.notion_client, "create_child_page", _fake_create)

    tools = notion_tools.build_notion_tools(_scope())
    assert len(tools) == 1
    out = str(
        tools[0](
            parent,
            "Gap follow-up",
            "Details here.",
            "https://drive.google.com/file/d/abc",
        )
    )
    assert "22222222" in out
    assert "url=" in out


def test_notion_read_rejects_unknown_page(monkeypatch) -> None:
    allowed = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "true")
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", allowed)
    get_settings.cache_clear()

    monkeypatch.setattr(
        notion_tools.notion_client,
        "build_notion_client",
        lambda _t: object(),
    )
    tools = notion_tools.build_notion_tools(_scope())
    other = "33333333-3333-4333-8333-333333333333"
    out = str(tools[0](other))
    assert "not_allowlisted" in out or "invalid" in out
