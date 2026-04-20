"""Neuuf primary coordinator agent (personal assistant style)."""

from collections.abc import Callable
from typing import Any, Literal

from strands import Agent
from strands_tools import current_time

from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.default_model import get_default_model
from iso_agent.l3_runtime.integrations.google_workspace_mcp import (
    get_google_workspace_mcp_tools,
)
from iso_agent.l3_runtime.integrations.notion_mcp import (
    build_notion_mcp_oauth_tool,
    get_notion_mcp_tools,
)
from iso_agent.l3_runtime.prompts import load_role_prompt
from iso_agent.l3_runtime.team.subagents import build_specialist_tools
from iso_agent.l3_runtime.tools.audit_tools import build_audit_tools
from iso_agent.l3_runtime.tools.calendar_tools import build_calendar_tools
from iso_agent.l3_runtime.tools.coding_tools import build_coding_tools
from iso_agent.l3_runtime.tools.drive_tools import build_drive_tools
from iso_agent.l3_runtime.tools.gap_tools import build_gap_tools
from iso_agent.l3_runtime.tools.notion_tools import build_notion_tools


def build_neuuf_coordinator(
    scope: UserScope,
    *,
    google_chat_mode: Literal["dm", "room"] = "dm",
    include_coding_tools: bool = True,
    include_notion_mcp_oauth_tool: bool = False,
    callback_handler: Callable[..., Any] | None = None,
) -> Agent:
    """Return the Neuuf ISO coordinator :class:`~strands.agent.agent.Agent` for this scope.

    Args:
        scope: User-scoped memory and thread partition.
        google_chat_mode: ``room`` appends stricter shared-space instructions (Phase 5).
        include_notion_mcp_oauth_tool: When true, register in-process Notion MCP browser login
            (local interactive CLI only; keep false for Chat and one-shot ``--query``).
        include_coding_tools: When true (default), register ``python_repl``, ``editor``,
            ``shell``, and ``journal``. Google Chat ingress should pass false.
        callback_handler: Optional Strands callback (e.g. Rich console for local CLI).
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
    if include_coding_tools:
        coding_precursor = load_role_prompt("coding_precursor")
        system_prompt = f"{system_prompt}\n\n---\n\n{coding_precursor}"
    oauth_tool = (
        build_notion_mcp_oauth_tool(scope) if include_notion_mcp_oauth_tool else []
    )
    mcp_notion = get_notion_mcp_tools(scope)
    mcp_google = get_google_workspace_mcp_tools()
    tools = [
        current_time,
        *build_specialist_tools(scope),
        *build_gap_tools(scope),
        *build_calendar_tools(scope),
        *build_audit_tools(scope),
        *build_drive_tools(scope),
        *(mcp_google or []),
        *build_notion_tools(scope),
        *oauth_tool,
        *(mcp_notion or []),
        *build_coding_tools(scope, enabled=include_coding_tools),
    ]
    agent_kw: dict[str, Any] = {
        "model": get_default_model(),
        "system_prompt": system_prompt,
        "tools": tools,
        "trace_attributes": {"user.key": scope.user_key, "thread.key": scope.thread_key},
    }
    if callback_handler is not None:
        agent_kw["callback_handler"] = callback_handler
    return Agent(**agent_kw)
