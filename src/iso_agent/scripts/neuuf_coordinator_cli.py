"""CLI: Neuuf ISO coordinator (always Neuuf team; ignores ``ISO_AGENT_PRIMARY_MODE``)."""

from __future__ import annotations

import argparse
import os
import sys

from strands.handlers.callback_handler import PrintingCallbackHandler

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.agents import create_neuuf_coordinator_agent


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
            "LLM is AWS Bedrock only (Strands BedrockModel): configure AWS credentials and region "
            "(e.g. AWS_PROFILE, AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, or instance role) and "
            "optional ISO_AGENT_BEDROCK_MODEL_ID / ISO_AGENT_BEDROCK_REGION_NAME.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    if args.query is not None:
        _print_agent_result(agent, agent(args.query))
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
            _print_agent_result(agent, agent(line))
            print()
        except Exception as exc:  # noqa: BLE001 — surface any model/tool error in the REPL
            print(f"error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
