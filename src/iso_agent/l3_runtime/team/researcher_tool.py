"""Researcher specialist as a coordinator :func:`~strands.tools.decorator.tool`."""

from __future__ import annotations

from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations.perplexity import get_perplexity_mcp_tools
from iso_agent.l3_runtime.team.specialist_base import build_inner_specialist


def build_researcher_tools(scope: UserScope) -> list[Any]:
    """Return ``neuuf_researcher`` tool (inner agent + optional Perplexity MCP)."""
    research_tools = get_perplexity_mcp_tools() or []
    research = build_inner_specialist(scope, "researcher", extra_tools=research_tools)
    research_desc = (
        "ISO-aware research specialist with Perplexity web search when "
        "PERPLEXITY_API_KEY and ISO_AGENT_PERPLEXITY_TRANSPORT=docker are set; "
        "otherwise model-only."
    )

    @tool(
        name="neuuf_researcher",
        description=research_desc,
    )
    def neuuf_researcher(query: str) -> str:
        """Run the researcher sub-agent on the given query."""
        return str(research(query))

    return [neuuf_researcher]
