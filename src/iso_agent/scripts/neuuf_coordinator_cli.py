"""CLI: Neuuf ISO coordinator (always Neuuf team; ignores ``ISO_AGENT_PRIMARY_MODE``)."""

from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user import UserScope
from iso_agent.l3_runtime.agents import create_neuuf_coordinator_agent


def main() -> None:
    """Run a one-shot Neuuf coordinator message (Bedrock or configured model)."""
    ctx = inbound_dm(user_id="local-dev", space="dm", thread="neuuf-cli")
    scope = UserScope.from_context(ctx)
    agent = create_neuuf_coordinator_agent(scope)
    query = (
        "Summarize how you would help Neuuf with ISO 9001 and which specialists you would invoke."
    )
    print(str(agent(query)))


if __name__ == "__main__":
    main()
