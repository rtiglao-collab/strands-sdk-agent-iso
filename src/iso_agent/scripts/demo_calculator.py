"""Demo: scoped primary agent with calculator tool (migrated from root `agent.py`)."""

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l1_router.handler import handle_user_message
from iso_agent.l2_user import UserScope


def main() -> None:
    """Run a one-shot demo message through L1 → L2 → L3."""
    ctx = inbound_dm(user_id="local-dev", space="dm", thread="main")
    scope = UserScope.from_context(ctx)
    try:
        print(handle_user_message(scope, "What is the square root of 1764"))
    except Exception as exc:
        print(
            f"Model call failed: {exc}. Set ANTHROPIC_API_KEY for default Anthropic Sonnet, or "
            "ISO_AGENT_LLM_PROVIDER=bedrock with AWS credentials."
        )


if __name__ == "__main__":
    main()
