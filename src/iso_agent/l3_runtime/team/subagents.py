"""Aggregate Neuuf specialist tools (agents-as-tools).

Each specialist lives in its own module under ``team/`` (mirrors
``samples/02-samples/05-personal-assistant/``). This module only composes them
for :func:`build_neuuf_coordinator`.
"""

from __future__ import annotations

from typing import Any

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.comms_tool import build_comms_tools
from iso_agent.l3_runtime.team.gap_analyst_tool import build_gap_analyst_tools
from iso_agent.l3_runtime.team.governance_tool import build_governance_tools
from iso_agent.l3_runtime.team.researcher_tool import build_researcher_tools


def build_specialist_tools(scope: UserScope) -> list[Any]:
    """Build coordinator tools (wrappers around inner specialist agents)."""
    return [
        *build_researcher_tools(scope),
        *build_governance_tools(scope),
        *build_gap_analyst_tools(scope),
        *build_comms_tools(scope),
    ]
