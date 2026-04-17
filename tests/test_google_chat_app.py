"""Tests for the Google Chat FastAPI webhook."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from iso_agent.adapters import google_chat_app as app_mod


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ISO_AGENT_CHAT_WEBHOOK_SECRET", "test-secret")
    monkeypatch.delenv("ISO_AGENT_CHAT_ALLOW_INSECURE", raising=False)
    monkeypatch.setenv("ISO_AGENT_CHAT_DEDUPE_TTL_SECONDS", "300")

    def _stub(ctx: object, text: str) -> str:
        del ctx
        return "echo:" + text

    monkeypatch.setattr(app_mod, "handle_google_chat_turn", _stub)
    app_mod.reset_chat_dedupe_for_tests()
    app_mod.reset_chat_metrics_for_tests()
    return TestClient(app_mod.app)


def test_google_chat_webhook_ok(client: TestClient) -> None:
    body = {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/s1/messages/m1",
            "text": "ping",
            "sender": {"name": "users/u1"},
            "thread": {"name": "spaces/s1/threads/th1"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    r = client.post(
        "/google-chat",
        json=body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    assert r.status_code == 200
    assert r.json() == {"text": "echo:ping"}
    assert r.headers["x-iso-agent-request-id"]


def test_google_chat_webhook_bad_secret(client: TestClient) -> None:
    body = {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/s1/messages/m1",
            "text": "ping",
            "sender": {"name": "users/u1"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    r = client.post(
        "/google-chat",
        json=body,
        headers={"x-iso-agent-chat-secret": "wrong"},
    )
    assert r.status_code == 401


def test_google_chat_webhook_no_secret_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ISO_AGENT_CHAT_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("ISO_AGENT_CHAT_ALLOW_INSECURE", raising=False)
    c = TestClient(app_mod.app)
    r = c.post("/google-chat", json={})
    assert r.status_code == 503


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_google_chat_added_to_space_dm(client: TestClient) -> None:
    body = {
        "type": "ADDED_TO_SPACE",
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    r = client.post(
        "/google-chat",
        json=body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    assert r.status_code == 200
    assert "Thanks for adding me" in r.json()["text"]


def test_google_chat_duplicate_event_ignored(client: TestClient) -> None:
    body = {
        "type": "MESSAGE",
        "eventTime": "2026-04-17T00:00:00.000000Z",
        "message": {
            "name": "spaces/s1/messages/m1",
            "text": "ping",
            "sender": {"name": "users/u1"},
            "thread": {"name": "spaces/s1/threads/th1"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    first = client.post(
        "/google-chat",
        json=body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    second = client.post(
        "/google-chat",
        json=body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    assert first.status_code == 200
    assert first.json() == {"text": "echo:ping"}
    assert second.status_code == 200
    assert second.json() == {"text": "Already processed this event."}


def test_google_chat_request_id_passthrough(client: TestClient) -> None:
    body = {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/s1/messages/m2",
            "text": "ping",
            "sender": {"name": "users/u1"},
            "thread": {"name": "spaces/s1/threads/th2"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    r = client.post(
        "/google-chat",
        json=body,
        headers={
            "x-iso-agent-chat-secret": "test-secret",
            "x-request-id": "abc-123",
        },
    )
    assert r.status_code == 200
    assert r.headers["x-iso-agent-request-id"] == "abc-123"


def test_google_chat_metrics_endpoint_counts(client: TestClient) -> None:
    msg_body = {
        "type": "MESSAGE",
        "eventTime": "2026-04-18T00:00:00.000000Z",
        "message": {
            "name": "spaces/s1/messages/m9",
            "text": "ping",
            "sender": {"name": "users/u1"},
            "thread": {"name": "spaces/s1/threads/th9"},
        },
        "space": {"name": "spaces/s1", "type": "DM"},
    }
    added_body = {"type": "ADDED_TO_SPACE", "space": {"name": "spaces/s1", "type": "DM"}}

    ok = client.post(
        "/google-chat",
        json=msg_body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    dup = client.post(
        "/google-chat",
        json=msg_body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    onboard = client.post(
        "/google-chat",
        json=added_body,
        headers={"x-iso-agent-chat-secret": "test-secret"},
    )
    assert ok.status_code == 200
    assert dup.status_code == 200
    assert onboard.status_code == 200

    m = client.get("/chat-metrics")
    assert m.status_code == 200
    data = m.json()
    assert data["received"] == 3
    assert data["duplicate"] == 1
    assert data["onboarding"] == 1
    assert data["turn_success"] == 1
