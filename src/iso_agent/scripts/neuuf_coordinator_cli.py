"""CLI: Neuuf ISO coordinator (always Neuuf team; ignores ``ISO_AGENT_PRIMARY_MODE``)."""

from __future__ import annotations

import argparse
import os
import sys

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.agents import create_neuuf_coordinator_agent


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
    args = parser.parse_args()

    if not args.plain_console:
        # Show rich UI for tools in CLI
        os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

    ctx = inbound_dm(user_id="local-dev", space="dm", thread="neuuf-cli")
    scope = UserScope.from_context(ctx)
    try:
        agent = create_neuuf_coordinator_agent(scope)
    except Exception as exc:
        print(
            f"Failed to initialize the coordinator agent: {exc}. "
            "Set ANTHROPIC_API_KEY for default Anthropic Sonnet, or ISO_AGENT_LLM_PROVIDER=bedrock "
            "with AWS credentials for Bedrock.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    if args.query is not None:
        print(str(agent(args.query)))
        return

    print("Neuuf ISO coordinator — type 'exit', 'quit', or Ctrl+D to stop.")
    print(
        "Tip: STRANDS_TOOL_CONSOLE_MODE is enabled for clearer tool traces "
        "(use --plain-console to disable)."
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
            print(str(agent(line)))
            print()
        except Exception as exc:  # noqa: BLE001 — surface any model/tool error in the REPL
            print(f"error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
