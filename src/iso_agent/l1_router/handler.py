"""L1 entry: map inbound text to a scoped L3 agent run."""

from iso_agent.config import get_settings
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.agents import create_demo_agent, create_neuuf_coordinator_agent


def handle_user_message(scope: UserScope, text: str) -> str:
    """Run the primary agent for this user scope and return the final text."""
    settings = get_settings()
    if settings.primary_mode == "neuuf":
        agent = create_neuuf_coordinator_agent(scope)
    else:
        agent = create_demo_agent(scope)
    return str(agent(text))
