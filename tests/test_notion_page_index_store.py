"""Tests for persisted Notion page index."""

from __future__ import annotations

from pathlib import Path

import pytest

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import memory_layout, notion_page_index_store
from iso_agent.l2_user.user_scope import UserScope


def _scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> UserScope:
    monkeypatch.setattr(memory_layout, "REPO_ROOT", tmp_path)
    get_settings.cache_clear()
    return UserScope.from_context(inbound_dm(user_id="index-test", space="dm", thread="t"))


def test_merge_and_search_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    hits = [
        {
            "id": "11111111-1111-4111-8111-111111111111",
            "url": "https://notion.so/a",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Engineering Dashboard", "type": "text"}],
                }
            },
            "parent": {"type": "workspace", "workspace": True},
        },
        {
            "id": "22222222-2222-4222-8222-222222222222",
            "url": "https://notion.so/b",
            "properties": {},
            "parent": {"type": "page_id", "page_id": "11111111-1111-4111-8111-111111111111"},
        },
    ]
    n = notion_page_index_store.merge_discovery_hits(scope, hits)
    assert n == 2
    found = notion_page_index_store.search_titles(scope, "engineering")
    assert len(found) == 1
    assert found[0].id == "11111111-1111-4111-8111-111111111111"
    both = notion_page_index_store.search_titles(
        scope,
        "engineering",
        match_all_words=True,
        max_results=25,
    )
    assert len(both) == 1
    assert both[0].id == "11111111-1111-4111-8111-111111111111"
    st = notion_page_index_store.format_status(scope)
    assert "entries=<2>" in st
    get_settings.cache_clear()


def test_search_titles_match_all_words_disambiguates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "url": "https://notion.so/a",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Corporate Engineering Home", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": "22222222-2222-4222-8222-222222222222",
                "url": "https://notion.so/b",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Engineering Quality Docs", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    loose = notion_page_index_store.search_titles(scope, "engineering")
    assert len(loose) == 2
    strict = notion_page_index_store.search_titles(
        scope, "corporate engineering", match_all_words=True
    )
    assert len(strict) == 1
    assert strict[0].title == "Corporate Engineering Home"


def test_format_page_metadata_workspace_hub_and_nested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    hub = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": hub,
                "url": "https://notion.so/h",
                "last_edited_time": "2026-04-01T12:00:00.000Z",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Corporate Engineering Home", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": child,
                "url": "https://notion.so/c",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Project Tracker", "type": "text"}],
                    }
                },
                "parent": {"type": "page_id", "page_id": hub},
            },
        ],
    )
    hub_meta = notion_page_index_store.format_page_metadata_report(scope, hub)
    assert "workspace" in hub_meta
    assert "ancestor_titles_top_down=Corporate Engineering Home" in hub_meta
    child_meta = notion_page_index_store.format_page_metadata_report(scope, child)
    assert "ancestor_titles_top_down=Corporate Engineering Home > Project Tracker" in child_meta


def test_format_subtree_lists_only_descendants_of_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    hub = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    sibling = "33333333-3333-4333-8333-333333333333"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": hub,
                "url": "https://notion.so/h",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Corporate Engineering Home", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": child,
                "url": "https://notion.so/c",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Project Tracker", "type": "text"}],
                    }
                },
                "parent": {"type": "page_id", "page_id": hub},
            },
            {
                "id": sibling,
                "url": "https://notion.so/s",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Engineering Dashboard", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    out = notion_page_index_store.format_subtree_under_parent(scope, hub)
    assert "Corporate Engineering Home" in out
    assert "Project Tracker" in out
    assert "Engineering Dashboard" not in out


def test_format_index_outline_groups_workspace_and_nested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    parent = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": parent,
                "url": "https://notion.so/p",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Corporate Engineering Home", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": child,
                "url": "https://notion.so/c",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Runbook", "type": "text"}],
                    }
                },
                "parent": {"type": "page_id", "page_id": parent},
            },
        ],
    )
    out = notion_page_index_store.format_index_outline(scope, max_lines=80)
    assert "Workspace top-level" in out
    assert "Corporate Engineering Home" in out
    assert "parent_title='Corporate Engineering Home'" in out
    assert "Runbook" in out


def test_parent_page_id_from_entry_and_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    parent = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    hits = [
        {
            "id": parent,
            "url": "https://notion.so/p",
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Workspace Root", "type": "text"}],
                }
            },
            "parent": {"type": "workspace", "workspace": True},
        },
        {
            "id": child,
            "url": "https://notion.so/c",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Child Page", "type": "text"}],
                }
            },
            "parent": {"type": "page_id", "page_id": parent},
        },
    ]
    notion_page_index_store.merge_discovery_hits(scope, hits)
    loaded = notion_page_index_store.load_index(scope)
    child_entry = next(e for e in loaded.entries if e.id == child)
    assert notion_page_index_store.parent_page_id_from_entry(child_entry) == parent
    under = notion_page_index_store.list_index_children_of_parent(scope, parent_id=parent)
    assert len(under) == 1
    assert under[0].id == child


def test_resolve_unique_page_id_by_title_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    pid_a = "11111111-1111-4111-8111-111111111111"
    pid_b = "22222222-2222-4222-8222-222222222222"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": pid_a,
                "url": "https://notion.so/a",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "ISO Drafts Bin", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
            {
                "id": pid_b,
                "url": "https://notion.so/b",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "ISO Archive", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    resolved, err = notion_page_index_store.resolve_unique_page_id_by_title_hint(
        scope, {pid_a}, "drafts", label="test"
    )
    assert err == ""
    assert resolved == pid_a
    ambig, err2 = notion_page_index_store.resolve_unique_page_id_by_title_hint(
        scope, {pid_a, pid_b}, "iso", label="test"
    )
    assert ambig is None
    assert "ambiguous_title_hint" in err2


def test_merge_with_empty_hits_clears_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "url": "https://notion.so/a",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Solo", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    assert len(notion_page_index_store.load_index(scope).entries) == 1
    n = notion_page_index_store.merge_discovery_hits(scope, [])
    assert n == 0
    assert len(notion_page_index_store.load_index(scope).entries) == 0


def test_merge_refresh_replaces_previous_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each refresh replaces the index so stale ids do not accumulate."""
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    a = "11111111-1111-4111-8111-111111111111"
    b = "22222222-2222-4222-8222-222222222222"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": a,
                "url": "https://notion.so/a",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Only A", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    assert len(notion_page_index_store.load_index(scope).entries) == 1
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": b,
                "url": "https://notion.so/b",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Only B", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    loaded = notion_page_index_store.load_index(scope)
    assert len(loaded.entries) == 1
    assert loaded.entries[0].id == b


def test_bootstrap_draft_parent_candidates_orders_workspace_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ISO_AGENT_NOTION_ENABLED", "false")
    get_settings.cache_clear()
    scope = _scope(tmp_path, monkeypatch)
    a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    notion_page_index_store.merge_discovery_hits(
        scope,
        [
            {
                "id": b,
                "url": "https://notion.so/b",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Zebra Page", "type": "text"}],
                    }
                },
                "parent": {"type": "page_id", "page_id": a},
            },
            {
                "id": a,
                "url": "https://notion.so/a",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Alpha Top", "type": "text"}],
                    }
                },
                "parent": {"type": "workspace", "workspace": True},
            },
        ],
    )
    cand = notion_page_index_store.bootstrap_draft_parent_candidates(
        scope, title_needle="", max_results=10
    )
    assert [e.id for e in cand] == [a, b]
