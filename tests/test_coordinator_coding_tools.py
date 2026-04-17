"""Coding tools merge on the Neuuf coordinator."""

from __future__ import annotations

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="coding-test", space="dm", thread="t"))


def test_coordinator_includes_coding_tools_by_default() -> None:
    agent = build_neuuf_coordinator(_scope())
    for name in ("python_repl", "editor", "shell", "journal"):
        assert name in agent.tool_names


def test_coordinator_omits_coding_tools_when_disabled() -> None:
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "python_repl" not in agent.tool_names
    assert "shell" not in agent.tool_names
