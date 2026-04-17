"""Tests for persisted Notion allowlist merge and mutations."""

from __future__ import annotations

from pathlib import Path

import pytest

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import memory_layout, notion_allowlist_store
from iso_agent.l2_user.user_scope import UserScope


def _scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> UserScope:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    get_settings.cache_clear()
    return UserScope.from_context(inbound_dm(user_id="allowlist-test", space="dm", thread="t"))


def test_persisted_roundtrip_and_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    page = "11111111-1111-4111-8111-111111111111"
    parent = "22222222-2222-4222-8222-222222222222"
    notion_allowlist_store.save_persisted_allowlist(scope, {page}, {parent})
    p2, par2 = notion_allowlist_store.load_persisted_allowlist(scope)
    assert p2 == {page}
    assert par2 == {parent}

    env_page = "33333333-3333-4333-8333-333333333333"
    env_parent = "44444444-4444-4444-8444-444444444444"
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PAGE_IDS", env_page)
    monkeypatch.setenv("ISO_AGENT_NOTION_ALLOWED_PARENT_IDS", env_parent)
    get_settings.cache_clear()
    s = get_settings()
    merged_pages = notion_allowlist_store.merged_page_ids(scope, s)
    merged_parents = notion_allowlist_store.merged_parent_ids(scope, s)
    assert page in merged_pages
    assert env_page in merged_pages
    assert parent in merged_parents
    assert env_parent in merged_parents


def test_add_remove_read_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    pid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    ok, code = notion_allowlist_store.add_persisted_read_page(scope, pid)
    assert ok and code == "ok"
    ok2, code2 = notion_allowlist_store.add_persisted_read_page(scope, pid)
    assert ok2 and code2 == "already_present"
    ok3, code3 = notion_allowlist_store.remove_persisted_read_page(scope, pid)
    assert ok3 and code3 == "ok"
    ok4, code4 = notion_allowlist_store.remove_persisted_read_page(scope, pid)
    assert not ok4 and code4 == "not_in_persisted_allowlist"
