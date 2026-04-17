"""Inbound channel context: identity must come from the platform payload."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class InboundContext:
    """Normalized inbound event (replace with your Chat or HTTP payload mapping)."""

    user_id: str
    space: str
    thread: str
    channel: str = "dev"
    #: ``dm`` = 1:1 DM; ``space`` = shared room; ``dev`` = local / non-Chat.
    space_kind: Literal["dm", "space", "dev"] = "dev"


def inbound_dm(*, user_id: str, space: str, thread: str) -> InboundContext:
    """Build a DM-shaped context for local development."""
    return InboundContext(
        user_id=user_id,
        space=space,
        thread=thread,
        channel="dev",
        space_kind="dm",
    )
