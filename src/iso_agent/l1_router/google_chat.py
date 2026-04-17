"""Google Chat HTTP event parsing and L1 → L3 turn handling (Phase 5)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from iso_agent.l1_router.context import InboundContext
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GoogleChatParseResult:
    """Result of parsing a Google Chat JSON payload."""

    ok: bool
    context: InboundContext | None = None
    text: str | None = None
    error: str | None = None


def parse_google_chat_event(body: dict[str, Any]) -> GoogleChatParseResult:
    """Parse a synchronous Google Chat **MESSAGE** event into :class:`InboundContext`.

    Identity fields are taken only from the structured payload (never from free text).
    """
    event_type = str(body.get("type", "")).upper()
    if event_type != "MESSAGE":
        et = event_type or "missing"
        return GoogleChatParseResult(
            ok=False,
            error=f"unsupported_event_type=<{et}>",
        )

    message = body.get("message")
    if not isinstance(message, dict):
        return GoogleChatParseResult(ok=False, error="missing_message")

    text = str(message.get("text", "")).strip()
    if not text:
        return GoogleChatParseResult(ok=False, error="empty_message_text")

    sender = message.get("sender")
    user_id = "unknown"
    if isinstance(sender, dict):
        user_id = str(sender.get("name", sender.get("displayName", "unknown")))

    space = body.get("space")
    if not isinstance(space, dict):
        return GoogleChatParseResult(ok=False, error="missing_space")
    space_name = str(space.get("name", "spaces/unknown"))
    space_type = str(space.get("type", "")).upper()

    if space_type == "DM":
        space_kind: Literal["dm", "space", "dev"] = "dm"
    elif space_type in {"ROOM", "SPACE"}:
        space_kind = "space"
    else:
        space_kind = "space"

    thread_obj = message.get("thread")
    if isinstance(thread_obj, dict) and thread_obj.get("name"):
        thread_key = str(thread_obj["name"])
    else:
        thread_key = str(message.get("name", "thread/main"))
    thread = thread_key.split("/")[-1] if "/" in thread_key else thread_key

    ctx = InboundContext(
        user_id=user_id,
        space=space_name,
        thread=thread,
        channel="google_chat",
        space_kind=space_kind,
    )
    return GoogleChatParseResult(ok=True, context=ctx, text=text)


def handle_google_chat_turn(ctx: InboundContext, text: str) -> str:
    """Run the Neuuf coordinator for this Chat turn (DM vs shared-room policy)."""
    scope = UserScope.from_context(ctx)
    mode: Literal["dm", "room"] = "room" if ctx.space_kind == "space" else "dm"
    logger.debug(
        "google_chat_turn user_key=<%s> space_kind=<%s> mode=<%s>",
        scope.user_key,
        ctx.space_kind,
        mode,
    )
    agent = build_neuuf_coordinator(
        scope,
        google_chat_mode=mode,
        include_coding_tools=False,
    )
    return str(agent(text))
