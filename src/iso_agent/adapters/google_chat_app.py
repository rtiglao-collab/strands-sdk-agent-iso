"""FastAPI app: Google Chat synchronous HTTP endpoint (Phase 5)."""

from __future__ import annotations

import hmac
import logging
import os
import time
from collections import OrderedDict
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response

from iso_agent.l1_router.google_chat import (
    GoogleChatParseResult,
    handle_google_chat_turn,
    parse_google_chat_event,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="iso-agent Google Chat webhook", version="0.1.0")

_SECRET_HEADER = "x-iso-agent-chat-secret"
_REQUEST_ID_HEADER = "x-iso-agent-request-id"


class _RecentEventStore:
    """Simple in-memory TTL dedupe store for webhook retries."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, float] = OrderedDict()

    def is_duplicate(self, event_key: str, *, now: float, ttl_s: int) -> bool:
        self._evict(now=now, ttl_s=ttl_s)
        if event_key in self._seen:
            return True
        self._seen[event_key] = now
        return False

    def _evict(self, *, now: float, ttl_s: int) -> None:
        cutoff = now - float(ttl_s)
        while self._seen:
            _, ts = next(iter(self._seen.items()))
            if ts >= cutoff:
                break
            self._seen.popitem(last=False)


_RECENT_EVENTS = _RecentEventStore()


class _ChatMetrics:
    """In-memory counters for webhook behavior."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {
            "received": 0,
            "duplicate": 0,
            "onboarding": 0,
            "parse_failed": 0,
            "turn_failed": 0,
            "turn_success": 0,
        }

    def inc(self, key: str) -> None:
        self._counts[key] = self._counts.get(key, 0) + 1

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)

    def reset(self) -> None:
        for k in list(self._counts):
            self._counts[k] = 0


_CHAT_METRICS = _ChatMetrics()


def reset_chat_dedupe_for_tests() -> None:
    """Clear recent-event cache for deterministic tests."""
    _RECENT_EVENTS._seen.clear()


def reset_chat_metrics_for_tests() -> None:
    """Clear in-memory chat counters for deterministic tests."""
    _CHAT_METRICS.reset()


def _verify_secret(request: Request) -> None:
    expected = os.environ.get("ISO_AGENT_CHAT_WEBHOOK_SECRET", "").strip()
    if not expected:
        if os.environ.get("ISO_AGENT_CHAT_ALLOW_INSECURE", "").lower() == "true":
            logger.warning("chat_webhook | no secret configured; insecure mode enabled")
            return
        raise HTTPException(status_code=503, detail="webhook secret not configured")
    got = request.headers.get(_SECRET_HEADER, "")
    exp_b = expected.encode("utf-8")
    got_b = got.encode("utf-8")
    if len(got_b) != len(exp_b) or not hmac.compare_digest(got_b, exp_b):
        raise HTTPException(status_code=401, detail="invalid webhook secret")


def _reply_text(text: str) -> dict[str, Any]:
    return {"text": text[:4096]}


def _request_id(request: Request) -> str:
    for header in (_REQUEST_ID_HEADER, "x-request-id"):
        value = request.headers.get(header, "").strip()
        if value:
            return value[:128]
    return str(uuid4())


def _dedupe_ttl_seconds() -> int:
    raw = os.environ.get("ISO_AGENT_CHAT_DEDUPE_TTL_SECONDS", "300").strip()
    try:
        val = int(raw)
    except ValueError:
        val = 300
    return max(10, min(val, 86400))


def _event_key(body: dict[str, Any]) -> str:
    event_type = str(body.get("type", "")).upper() or "UNKNOWN"
    event_time = str(body.get("eventTime", ""))
    message = body.get("message")
    msg_name = ""
    if isinstance(message, dict):
        msg_name = str(message.get("name", ""))
    # Keep key deterministic but privacy-safe (no message text).
    return f"{event_type}|{event_time}|{msg_name}"


def _welcome_text(body: dict[str, Any]) -> str:
    space = body.get("space")
    space_type = ""
    if isinstance(space, dict):
        space_type = str(space.get("type", "")).upper()
    if space_type == "DM":
        return (
            "Thanks for adding me. I can help with Neuuf ISO workflows, including "
            "gap tracking, audit cadence, and draft communications."
        )
    return (
        "Thanks for adding me to this space. I reply with group-safe summaries here; "
        "use DM for user-specific planning."
    )


@app.post("/google-chat")
async def google_chat_webhook(request: Request, response: Response) -> dict[str, Any]:
    """Handle Google Chat events; return synchronous JSON ``text``."""
    request_id = _request_id(request)
    response.headers[_REQUEST_ID_HEADER] = request_id
    _verify_secret(request)
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 — malformed JSON
        raise HTTPException(status_code=400, detail="invalid json") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="json must be an object")

    key = _event_key(body)
    event_type = str(body.get("type", "")).upper() or "UNKNOWN"
    logger.info(
        "request_id=<%s>, event_type=<%s>, key=<%s> | google chat webhook received",
        request_id,
        event_type,
        key,
    )
    _CHAT_METRICS.inc("received")
    ttl_s = _dedupe_ttl_seconds()
    if _RECENT_EVENTS.is_duplicate(key, now=time.time(), ttl_s=ttl_s):
        _CHAT_METRICS.inc("duplicate")
        logger.info(
            "request_id=<%s>, key=<%s> | google chat duplicate ignored",
            request_id,
            key,
        )
        return _reply_text("Already processed this event.")

    if event_type == "ADDED_TO_SPACE":
        _CHAT_METRICS.inc("onboarding")
        logger.info(
            "request_id=<%s>, key=<%s> | google chat onboarding handled",
            request_id,
            key,
        )
        return _reply_text(_welcome_text(body))

    parsed: GoogleChatParseResult = parse_google_chat_event(body)
    if not parsed.ok or parsed.context is None or parsed.text is None:
        _CHAT_METRICS.inc("parse_failed")
        logger.info(
            "request_id=<%s>, key=<%s>, error=<%s> | google chat parse failed",
            request_id,
            key,
            parsed.error,
        )
        return _reply_text("Sorry, I can only handle plain text messages in this integration.")

    try:
        out = handle_google_chat_turn(parsed.context, parsed.text)
    except Exception:  # noqa: BLE001 — surface safe message to Chat
        _CHAT_METRICS.inc("turn_failed")
        logger.exception(
            "request_id=<%s>, key=<%s> | google chat turn failed",
            request_id,
            key,
        )
        return _reply_text("Something went wrong processing that message.")

    _CHAT_METRICS.inc("turn_success")
    logger.info(
        "request_id=<%s>, key=<%s>, space_kind=<%s> | google chat turn completed",
        request_id,
        key,
        parsed.context.space_kind,
    )
    return _reply_text(out)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe for Cloud Run / k8s."""
    return {"status": "ok"}


@app.get("/chat-metrics")
async def chat_metrics() -> dict[str, int]:
    """Return in-memory Chat counters (ephemeral process-local view)."""
    return _CHAT_METRICS.snapshot()
