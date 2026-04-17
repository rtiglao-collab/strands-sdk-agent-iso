"""Tests for Google Chat JSON parsing."""

from iso_agent.l1_router.context import InboundContext
from iso_agent.l1_router.google_chat import parse_google_chat_event
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.team.coordinator import build_neuuf_coordinator


def _dm_body() -> dict:
    return {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/s1/messages/m1",
            "text": "hello iso",
            "sender": {"name": "users/u1", "displayName": "Pat"},
            "thread": {"name": "spaces/s1/threads/th1"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }


def test_parse_dm_ok() -> None:
    r = parse_google_chat_event(_dm_body())
    assert r.ok and r.context is not None and r.text is not None
    assert r.text == "hello iso"
    assert r.context.space_kind == "dm"
    assert r.context.channel == "google_chat"
    assert r.context.thread == "th1"


def test_parse_room_space_kind() -> None:
    body = _dm_body()
    body["space"]["type"] = "ROOM"
    r = parse_google_chat_event(body)
    assert r.ok and r.context is not None
    assert r.context.space_kind == "space"


def test_parse_unsupported_type() -> None:
    body = _dm_body()
    body["type"] = "ADDED_TO_SPACE"
    r = parse_google_chat_event(body)
    assert not r.ok
    assert r.error is not None


def test_room_mode_appends_suffix() -> None:
    ctx = InboundContext(
        user_id="u",
        space="spaces/x",
        thread="t1",
        channel="google_chat",
        space_kind="space",
    )
    scope = UserScope.from_context(ctx)
    agent = build_neuuf_coordinator(scope, google_chat_mode="room")
    assert "shared Google Chat" in agent.system_prompt
