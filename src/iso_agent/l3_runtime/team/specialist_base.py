"""Shared factory for inner specialist :class:`~strands.agent.agent.Agent` instances."""

from __future__ import annotations

from typing import Any

from strands import Agent

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.default_model import get_default_model
from iso_agent.l3_runtime.prompts import load_role_prompt


def specialist_trace_attributes(scope: UserScope) -> dict[str, str]:
    """OpenTelemetry-style trace fields for inner specialists."""
    return {"user.key": scope.user_key, "thread.key": scope.thread_key}


def build_inner_specialist(
    scope: UserScope,
    role_slug: str,
    *,
    extra_tools: list[Any] | None = None,
) -> Agent:
    """Return an inner ``Agent`` loaded from ``knowledge/agents/<role_slug>.md``."""
    body = load_role_prompt(role_slug)
    tools: list[Any] = list(extra_tools) if extra_tools else []
    return Agent(
        model=get_default_model(),
        system_prompt=body,
        tools=tools,
        trace_attributes=specialist_trace_attributes(scope),
    )
