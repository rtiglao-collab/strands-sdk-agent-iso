"""User scope passed into L3 so side effects land in the correct partition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from iso_agent.l1_router.context import InboundContext
from iso_agent.l2_user.memory_layout import ensure_user_memory_dir, stable_user_key


@dataclass(frozen=True, slots=True)
class UserScope:
    """Everything L3 needs to stay user-scoped."""

    user_key: str
    memory_root: Path
    thread_key: str

    @classmethod
    def from_context(cls, ctx: InboundContext) -> UserScope:
        """Build scope from inbound context (DM-first rules belong in L1)."""
        user_key = stable_user_key(ctx.user_id)
        memory_root = ensure_user_memory_dir(user_key)
        thread_key = f"{user_key}|{ctx.space}|{ctx.thread}"
        return cls(user_key=user_key, memory_root=memory_root, thread_key=thread_key)
