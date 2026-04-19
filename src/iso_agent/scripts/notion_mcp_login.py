"""CLI: one-shot OAuth login for Notion hosted MCP (writes ``mcp_oauth.json`` per user)."""

from __future__ import annotations

import argparse
import sys

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.integrations.notion_mcp import run_notion_mcp_interactive_login


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Notion MCP OAuth login — opens a browser, listens on the redirect URI from "
            "ISO_AGENT_NOTION_MCP_REDIRECT_URI, and saves tokens under memory/users/.../notion/."
        ),
    )
    parser.add_argument(
        "--user-id",
        default="local-dev",
        help="Inbound user id for memory scoping (default: local-dev, same as neuuf CLI).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the authorize URL only; do not open a browser window.",
    )
    args = parser.parse_args()
    ctx = inbound_dm(user_id=args.user_id, space="dm", thread="notion-mcp-login")
    scope = UserScope.from_context(ctx)
    try:
        run_notion_mcp_interactive_login(scope, open_browser=not args.no_browser)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
