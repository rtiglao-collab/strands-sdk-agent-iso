"""Tests for gap coordinator tools."""

from __future__ import annotations

from pathlib import Path

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.tools.gap_tools import build_gap_tools


def _scope(tmp_path: Path) -> UserScope:
    root = tmp_path / "u"
    root.mkdir(parents=True)
    return UserScope(user_key="u", memory_root=root, thread_key="u|s|t")


def test_gap_append_tool(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    tools = build_gap_tools(scope)
    assert len(tools) == 2
    append, _list_tool = tools[0], tools[1]
    msg = str(
        append(
            title="Doc gap",
            summary="Procedure PR-1 not reviewed this year.",
            severity="medium",
            suggested_owner_role="Process owner",
            iso_clause_refs="8.5.1",
            evidence_refs="",
        )
    )
    assert "saved gap_id=" in msg
    assert "error" not in msg.lower()


def test_gap_append_tool_validation_error(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    tools = build_gap_tools(scope)
    append = tools[0]
    msg = str(
        append(
            title="",
            summary="x",
            severity="low",
            suggested_owner_role="o",
        )
    )
    assert msg.startswith("error:")


def test_gap_list_tool(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    tools = build_gap_tools(scope)
    append, list_tool = tools[0], tools[1]
    str(append("One", "s1", "low", "a"))
    str(append("Two", "s2", "high", "b"))
    js = str(list_tool(limit=5))
    assert "One" in js and "Two" in js
    assert "[" in js
