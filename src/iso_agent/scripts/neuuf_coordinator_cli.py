"""CLI: Neuuf ISO coordinator (always Neuuf team; ignores ``ISO_AGENT_PRIMARY_MODE``)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from strands.handlers.callback_handler import PrintingCallbackHandler

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.agents import create_neuuf_coordinator_agent
from iso_agent.l3_runtime.cli import RichAgentConsoleCallback
from iso_agent.config import get_settings
from iso_agent.l3_runtime.integrations.notion_mcp import (
    consume_coordinator_reload_after_notion_mcp_oauth,
)


def _env_file_assigns_key(env_path: Path, key: str) -> bool:
    """True if ``key`` appears as ``key=...`` on an uncommented line in ``env_path``."""
    if not env_path.is_file():
        return False
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, _, _ = s.partition("=")
        if k.strip() == key:
            return True
    return False


def _apply_neuuf_cli_google_workspace_defaults() -> None:
    """Use Workspace MCP stdio + verbose MCP logs for local CLI unless env or ``.env`` already set them."""
    env_path = Path.cwd() / ".env"
    transport = "ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT"
    debug = "ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG"
    if transport not in os.environ and not _env_file_assigns_key(env_path, transport):
        os.environ[transport] = "stdio"
    if debug not in os.environ and not _env_file_assigns_key(env_path, debug):
        os.environ[debug] = "true"
    get_settings.cache_clear()


_MCP_DEBUG_LOGGERS_CONFIGURED = "_iso_agent_google_workspace_mcp_debug_handlers"


def _maybe_enable_google_workspace_mcp_debug_logging() -> None:
    """Attach stderr DEBUG handlers only to Strands/MCP loggers (never root DEBUG).

    Raising the root logger to DEBUG pulls in botocore, urllib3, markdown_it, etc., and can
    print AWS SigV4 signing material on stderr — avoid that.
    """
    raw = os.environ.get("ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG", "").strip().lower()
    if raw not in ("1", "true", "yes"):
        return
    fmt = logging.Formatter("%(levelname)s %(name)s | %(message)s")
    for name in (
        "strands.tools.mcp",
        "mcp",
        "iso_agent.l3_runtime.integrations.google_workspace_mcp",
    ):
        log = logging.getLogger(name)
        if getattr(log, _MCP_DEBUG_LOGGERS_CONFIGURED, False):
            continue
        setattr(log, _MCP_DEBUG_LOGGERS_CONFIGURED, True)
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(fmt)
        log.addHandler(handler)
        log.propagate = False


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

    :class:`~iso_agent.l3_runtime.cli.rich_agent_callback.RichAgentConsoleCallback` leaves the
    streamed Markdown on screen when the turn ends; skip printing ``str(result)`` for it too.
    """
    ch = getattr(agent, "callback_handler", None)
    if isinstance(ch, PrintingCallbackHandler):
        return
    if getattr(ch, "_rich_agent_console", False):
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
        help=(
            "Plain terminal: do not set STRANDS_TOOL_CONSOLE_MODE, and do not use Rich for "
            "assistant/tool streaming (default is Rich when stdout is a TTY)."
        ),
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
    _apply_neuuf_cli_google_workspace_defaults()
    _maybe_enable_google_workspace_mcp_debug_logging()

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

    use_rich = not args.plain_console and sys.stdout.isatty()
    if not args.plain_console:
        # Show rich UI for tools in CLI
        os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

    ctx = inbound_dm(user_id="local-dev", space="dm", thread="neuuf-cli")
    scope = UserScope.from_context(ctx)
    rich_cb: RichAgentConsoleCallback | None = RichAgentConsoleCallback() if use_rich else None
    try:
        agent = create_neuuf_coordinator_agent(
            scope,
            include_coding_tools=not args.no_coding_tools,
            include_notion_mcp_oauth_tool=(args.query is None and sys.stdin.isatty()),
            callback_handler=rich_cb,
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

    if use_rich:
        _welcome = Console(highlight=False, soft_wrap=True)
        _welcome.print(
            Panel.fit(
                "[bold]Neuuf ISO coordinator[/] — type [cyan]exit[/], [cyan]quit[/], or Ctrl+D.\n\n"
                "Notion: [dim]hybrid transport; notion_* via MCP after OAuth; raw notion_mcp_* "
                "for team lists; notion_mcp_oauth_interactive_login if needed.[/]\n\n"
                "[dim]STRANDS_TOOL_CONSOLE_MODE + Rich markdown streaming are on "
                "([cyan]--plain-console[/] to disable). "
                "BYPASS_TOOL_CONSENT defaults true; [cyan]--require-tool-consent[/] for [y/*].[/]",
                title="iso-neuuf-coordinator",
                border_style="blue",
            )
        )
    else:
        print("Neuuf ISO coordinator — type 'exit', 'quit', or Ctrl+D to stop.")
        print(
            "Notion: transport defaults to hybrid. After OAuth (mcp_oauth.json), **notion_*** QMS "
            "tools use hosted MCP, and extra **notion_mcp_*** tools may appear for teamspace-style "
            "queries; else call notion_mcp_oauth_interactive_login once."
        )
        print(
            "Tip: STRANDS_TOOL_CONSOLE_MODE is enabled for clearer tool traces "
            "(use --plain-console to disable). BYPASS_TOOL_CONSENT defaults to true so coding "
            "tools run without per-tool [y/*] prompts (use --require-tool-consent for "
            "confirmations)."
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
                        callback_handler=rich_cb,
                    )
                except Exception as exc:
                    print(
                        f"Failed to reload coordinator after Notion MCP OAuth: {exc}",
                        file=sys.stderr,
                    )
                else:
                    if use_rich:
                        Console(highlight=False, soft_wrap=True).print(
                            Markdown(
                                "**Coordinator reloaded** — Notion MCP session is ready; "
                                "**notion_*** tools are active."
                            )
                        )
                    else:
                        print(
                            "(Coordinator reloaded — Notion MCP session is ready; **notion_*** "
                            "tools are active.)"
                        )


if __name__ == "__main__":
    main()
