"""Neuuf primary coordinator agent (personal assistant style)."""

from typing import Literal

from strands import Agent
from strands_tools import current_time

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.prompts import load_role_prompt
from iso_agent.l3_runtime.team.subagents import build_specialist_tools
from iso_agent.l3_runtime.tools.audit_tools import build_audit_tools
from iso_agent.l3_runtime.tools.calendar_tools import build_calendar_tools
from iso_agent.l3_runtime.tools.drive_tools import build_drive_tools
from iso_agent.l3_runtime.tools.gap_tools import build_gap_tools
from iso_agent.l3_runtime.tools.notion_tools import build_notion_tools


def build_neuuf_coordinator(
    scope: UserScope,
    *,
    google_chat_mode: Literal["dm", "room"] = "dm",
) -> Agent:
    """Return the Neuuf ISO coordinator :class:`~strands.agent.agent.Agent` for this scope.

    Args:
        scope: User-scoped memory and thread partition.
        google_chat_mode: ``room`` appends stricter shared-space instructions (Phase 5).
    """
    base = load_role_prompt("neuuf_coordinator")
    scope_ctx = (
        f"Scope: user_key={scope.user_key}, memory_root={scope.memory_root}, "
        f"thread_key={scope.thread_key}."
    )
    if google_chat_mode == "room":
        room_rules = load_role_prompt("google_chat_room_suffix")
        system_prompt = f"{scope_ctx}\n\n{base}\n\n{room_rules}"
    else:
        system_prompt = f"{scope_ctx}\n\n{base}"
    tools = [
        current_time,
        *build_specialist_tools(scope),
        *build_gap_tools(scope),
        *build_calendar_tools(scope),
        *build_audit_tools(scope),
        *build_drive_tools(scope),
        *build_notion_tools(scope),
    ]
    return Agent(
        system_prompt=system_prompt,
        tools=tools,
        trace_attributes={"user.key": scope.user_key, "thread.key": scope.thread_key},
    )
