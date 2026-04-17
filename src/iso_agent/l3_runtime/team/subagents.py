"""Specialist sub-agents exposed to the coordinator as Strands tools.

Pattern mirrors ``samples/02-samples/05-personal-assistant/`` (agents-as-tools).
Each inner Agent is constructed per ``UserScope`` so traces and future tools stay partitioned.
"""

from __future__ import annotations

from typing import Any

from strands import Agent
from strands.tools.decorator import tool

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations.perplexity import get_perplexity_mcp_tools
from iso_agent.l3_runtime.prompts import load_role_prompt


def _trace(scope: UserScope) -> dict[str, str]:
    return {"user.key": scope.user_key, "thread.key": scope.thread_key}


def _inner_agent(
    scope: UserScope,
    role_slug: str,
    *,
    extra_tools: list[Any] | None = None,
) -> Agent:
    body = load_role_prompt(role_slug)
    tools: list[Any] = list(extra_tools) if extra_tools else []
    return Agent(
        system_prompt=body,
        tools=tools,
        trace_attributes=_trace(scope),
    )


def build_specialist_tools(scope: UserScope) -> list[Any]:
    """Build coordinator tools (wrappers around inner specialist agents)."""

    research_tools = get_perplexity_mcp_tools() or []
    research = _inner_agent(scope, "researcher", extra_tools=research_tools)
    governance = _inner_agent(scope, "governance_evidence")
    gaps = _inner_agent(scope, "gap_analyst")
    comms = _inner_agent(scope, "comms_coordinator")

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

    @tool(
        name="neuuf_comms",
        description="Draft Google Chat / human-facing messages (draft-only; human posts to Chat).",
    )
    def neuuf_comms(query: str) -> str:
        """Run the communications coordinator sub-agent."""
        return str(comms(query))

    return [neuuf_researcher, neuuf_governance, neuuf_gap_analyst, neuuf_comms]
