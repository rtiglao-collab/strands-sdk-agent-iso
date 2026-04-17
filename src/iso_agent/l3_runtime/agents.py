"""Agent factories (primary, specialists)."""

from strands import Agent
from strands_tools import calculator

from iso_agent.l2_user.user_scope import UserScope


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
    return Agent(tools=default_tools_for_scope(scope), system_prompt=system_prompt)
