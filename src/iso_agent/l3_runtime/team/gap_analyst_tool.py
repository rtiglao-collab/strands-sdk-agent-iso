"""Gap analyst specialist as a coordinator tool."""

from __future__ import annotations

from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.specialist_base import build_inner_specialist


def build_gap_analyst_tools(scope: UserScope) -> list[Any]:
    """Return ``neuuf_gap_analyst`` tool."""
    gaps = build_inner_specialist(scope, "gap_analyst")

    @tool(
        name="neuuf_gap_analyst",
        description=(
            "Structured gap analysis and hypotheses for QMS follow-up; coordinator may "
            "persist rows via gap_append_record (Phase 6)."
        ),
    )
    def neuuf_gap_analyst(query: str) -> str:
        """Run the gap analyst sub-agent."""
        return str(gaps(query))

    return [neuuf_gap_analyst]
