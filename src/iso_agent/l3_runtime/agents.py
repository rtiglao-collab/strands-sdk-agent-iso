"""Agent factories (primary, specialists)."""

from strands import Agent
from strands_tools import calculator

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.default_model import get_default_model


def default_tools_for_scope(scope: UserScope) -> list[object]:
    """Return tool objects for this scope (filter or inject per user here)."""
    del scope
    return [calculator]


def create_demo_agent(scope: UserScope) -> Agent:
    """Primary agent for demos; replace with model and tools from config."""
    system_prompt = (
        "You are the primary ISO agent host. "
        f"user_key={scope.user_key}, memory_root={scope.memory_root}, "
        f"thread_key={scope.thread_key}. "
        "Do not merge state across users; use scoped paths when writing files."
    )
    return Agent(
        model=get_default_model(),
        tools=default_tools_for_scope(scope),
        system_prompt=system_prompt,
    )


def create_neuuf_coordinator_agent(
    scope: UserScope,
    *,
    include_coding_tools: bool = True,
) -> Agent:
    """Neuuf ISO coordinator (agents-as-tools). See ``docs/NEUUF_ISO_PHASE_PLAN.md``."""
    from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator

    return build_neuuf_coordinator(scope, include_coding_tools=include_coding_tools)
