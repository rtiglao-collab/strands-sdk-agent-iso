"""Communications coordinator specialist as a coordinator tool."""

from __future__ import annotations

from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.specialist_base import build_inner_specialist


def build_comms_tools(scope: UserScope) -> list[Any]:
    """Return ``neuuf_comms`` tool."""
    comms = build_inner_specialist(scope, "comms_coordinator")

    @tool(
        name="neuuf_comms",
        description="Draft Google Chat / human-facing messages (draft-only; human posts to Chat).",
    )
    def neuuf_comms(query: str) -> str:
        """Run the communications coordinator sub-agent."""
        return str(comms(query))

    return [neuuf_comms]
