"""CLI: Neuuf ISO coordinator (always Neuuf team; ignores ``ISO_AGENT_PRIMARY_MODE``)."""

from __future__ import annotations

import argparse
import os
import sys

from strands.handlers.callback_handler import PrintingCallbackHandler

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.agents import create_neuuf_coordinator_agent
from iso_agent.l3_runtime.integrations.notion_mcp import (
    consume_coordinator_reload_after_notion_mcp_oauth,
)


def _format_agent_runtime_error(exc: Exception) -> str:
    """Return a short error line; add Bedrock hint when message looks like an auth/config miss."""
    msg = str(exc)
    lower = msg.lower()
    if "api_key" in lower or "auth_token" in lower or "authentication method" in lower:
        return (
            f"{msg} | hint: this host uses Amazon Bedrock only — configure AWS credentials "
            "and region (see README Model providers)"
        )
    return msg


def _print_agent_result(agent: object, result: object) -> None:
    """Emit final text only when stdout was not already streamed by the agent callback.

    Strands :class:`~strands.agent.agent.Agent` defaults to :class:`PrintingCallbackHandler`,
    which prints assistant tokens as they arrive. The CLI used to also ``print(str(result))``,
    which duplicated the full reply for REPL and ``--query`` runs.
    """
    ch = getattr(agent, "callback_handler", None)
    if isinstance(ch, PrintingCallbackHandler):
        return
    print(str(result))


def main() -> None:
    """Run the Neuuf coordinator interactively or with a single ``--query``."""
    parser = argparse.ArgumentParser(
        description=(
            "Neuuf ISO coordinator CLI (local dev). Same coordinator stack as Google Chat ingress."
        ),
    )
    parser.add_argument(
        "--query",
        type=str,
        metavar="TEXT",
        help="Send one message then exit (non-interactive).",
    )
    parser.add_argument(
        "--plain-console",
        action="store_true",
        help="Do not set STRANDS_TOOL_CONSOLE_MODE (disable richer tool UI in the terminal).",
    )
    parser.add_argument(
        "--no-coding-tools",
        action="store_true",
        help="Disable python_repl, editor, shell, and journal for this session (local CLI only).",
    )
    parser.add_argument(
        "--notion-mcp-login",
        action="store_true",
        help="Notion MCP OAuth login then exit (writes mcp_oauth.json under scoped memory).",
    )
    parser.add_argument(
        "--notion-mcp-login-user-id",
        default="local-dev",
        help="User id for memory scoping during --notion-mcp-login (default: local-dev).",
    )
    parser.add_argument(
        "--require-tool-consent",
        action="store_true",
        help=(
            "Require [y/*] confirmation for python_repl, editor, shell "
            "(Strands BYPASS_TOOL_CONSENT). Default: CLI opts out for autonomous tool runs."
        ),
    )
    args = parser.parse_args()

    if args.notion_mcp_login:
        from iso_agent.l3_runtime.integrations.notion_mcp import run_notion_mcp_interactive_login

        ctx = inbound_dm(
            user_id=args.notion_mcp_login_user_id, space="dm", thread="notion-mcp-login"
        )
        scope = UserScope.from_context(ctx)
        run_notion_mcp_interactive_login(scope, open_browser=True)
        return

    if args.require_tool_consent:
        os.environ["BYPASS_TOOL_CONSENT"] = "false"
    else:
        # Without this, strands_tools block each repl/editor/shell with a tty prompt
        os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

    if not args.plain_console:
        # Show rich UI for tools in CLI
        os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

    ctx = inbound_dm(user_id="local-dev", space="dm", thread="neuuf-cli")
    scope = UserScope.from_context(ctx)
    try:
        agent = create_neuuf_coordinator_agent(
            scope,
            include_coding_tools=not args.no_coding_tools,
            include_notion_mcp_oauth_tool=(args.query is None and sys.stdin.isatty()),
        )
    except Exception as exc:
        print(
            f"Failed to initialize the coordinator agent: {exc}. "
            "The coordinator uses Amazon Bedrock only — configure AWS credentials and region.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    if args.query is not None:
        try:
            _print_agent_result(agent, agent(args.query))
        except Exception as exc:  # noqa: BLE001
            print(f"error: {_format_agent_runtime_error(exc)}", file=sys.stderr)
            raise SystemExit(1) from None
        return

    print("Neuuf ISO coordinator — type 'exit', 'quit', or Ctrl+D to stop.")
    print(
        "Notion MCP: transport defaults to hybrid. With mcp_oauth.json you get "
        "notion_mcp_* tools; else ask the agent to call notion_mcp_oauth_interactive_login "
        "once, then ask for teamspaces."
    )
    print(
        "Tip: STRANDS_TOOL_CONSOLE_MODE is enabled for clearer tool traces "
        "(use --plain-console to disable). BYPASS_TOOL_CONSENT defaults to true so coding tools "
        "run without per-tool [y/*] prompts (use --require-tool-consent for confirmations)."
    )
    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit", "bye"}:
            break
        try:
            _print_agent_result(agent, agent(line))
            print()
        except Exception as exc:  # noqa: BLE001 — surface any model/tool error in the REPL
            print(f"error: {_format_agent_runtime_error(exc)}", file=sys.stderr)
        else:
            if consume_coordinator_reload_after_notion_mcp_oauth():
                try:
                    agent = create_neuuf_coordinator_agent(
                        scope,
                        include_coding_tools=not args.no_coding_tools,
                        include_notion_mcp_oauth_tool=True,
                    )
                except Exception as exc:
                    print(
                        f"Failed to reload coordinator after Notion MCP OAuth: {exc}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "(Coordinator reloaded — Notion MCP tools are now available. "
                        "Ask again for teamspaces.)"
                    )


if __name__ == "__main__":
    main()
