"""Coordinator appends coding precursor when coding tools are enabled."""

from __future__ import annotations

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="precursor-test", space="dm", thread="t"))


def test_coding_precursor_in_system_prompt_when_coding_enabled() -> None:
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=True)
    assert "Before coding (iso-agent)" in agent.system_prompt


def test_coding_precursor_absent_when_coding_disabled() -> None:
    agent = build_neuuf_coordinator(_scope(), include_coding_tools=False)
    assert "Before coding (iso-agent)" not in agent.system_prompt
