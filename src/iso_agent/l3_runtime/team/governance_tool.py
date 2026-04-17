"""Governance / evidence specialist as a coordinator tool."""

from __future__ import annotations

from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.specialist_base import build_inner_specialist


def build_governance_tools(scope: UserScope) -> list[Any]:
    """Return ``neuuf_governance`` tool."""
    governance = build_inner_specialist(scope, "governance_evidence")

    @tool(
        name="neuuf_governance",
        description=(
            "Governance and evidence alignment against ISO 9001 themes; clause-level "
            "remarks only when the user supplied excerpts in the same turn (Phase 7)."
        ),
    )
    def neuuf_governance(query: str) -> str:
        """Run the governance / evidence sub-agent."""
        return str(governance(query))

    return [neuuf_governance]
