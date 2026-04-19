"""Notion hosted MCP — OAuth discovery, dynamic client registration, PKCE (RFC 7636).

Uses synchronous :mod:`httpx` only (no authlib). Discovery URLs follow Notion's
`Integrating your own MCP client` guide: protected-resource metadata lives at
``https://mcp.notion.com/.well-known/oauth-protected-resource`` (host root), not
under ``/mcp/``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_UA = "iso-agent-notion-mcp/0.1"


def notion_mcp_origin_from_url(mcp_url: str) -> str:
    """Return ``scheme://netloc`` for the MCP host (e.g. ``https://mcp.notion.com``)."""
    parsed = urlparse(mcp_url.strip())
    if not parsed.scheme or not parsed.netloc:
        msg = "notion_mcp_url must include scheme and host"
        raise ValueError(msg)
    return f"{parsed.scheme}://{parsed.netloc}"


def _fetch_json(client: httpx.Client, url: str) -> dict[str, Any]:
    resp = client.get(
        url,
        headers={"Accept": "application/json", "User-Agent": _DEFAULT_UA},
        timeout=30.0,
    )
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        msg = f"expected JSON object from {url!r}"
        raise TypeError(msg)
    return cast(dict[str, Any], body)


def discover_oauth_endpoints(client: httpx.Client, *, mcp_url: str) -> dict[str, Any]:
    """Return authorization-server metadata (token, authorize, register URLs)."""
    origin = notion_mcp_origin_from_url(mcp_url)
    prm_url = f"{origin}/.well-known/oauth-protected-resource"
    prm = _fetch_json(client, prm_url)
    servers = prm.get("authorization_servers")
    if not isinstance(servers, list) or not servers:
        msg = "oauth protected resource metadata missing authorization_servers"
        raise ValueError(msg)
    first = servers[0]
    if not isinstance(first, str):
        msg = "authorization_servers[0] must be a string URL"
        raise TypeError(msg)
    as_url = first.rstrip("/")
    meta_url = f"{as_url}/.well-known/oauth-authorization-server"
    return _fetch_json(client, meta_url)


def generate_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` with S256 challenge."""
    verifier = secrets.token_urlsafe(48)[:128]
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def register_public_client(
    client: httpx.Client,
    *,
    registration_endpoint: str,
    redirect_uri: str,
    client_name: str = "iso-agent neuuf",
) -> tuple[str, str | None]:
    """POST dynamic client registration; return ``(client_id, client_secret_or_none)``."""
    payload = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    resp = client.post(
        registration_endpoint,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _DEFAULT_UA,
        },
        content=json.dumps(payload),
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        msg = "registration response must be a JSON object"
        raise TypeError(msg)
    cid = data.get("client_id")
    if not isinstance(cid, str) or not cid:
        msg = "registration response missing client_id"
        raise ValueError(msg)
    secret = data.get("client_secret")
    if secret is not None and not isinstance(secret, str):
        msg = "client_secret must be a string when present"
        raise TypeError(msg)
    return cid, secret


def build_authorization_url(
    *,
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
) -> str:
    from urllib.parse import urlencode

    q = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
    )
    return f"{authorization_endpoint}?{q}"


def exchange_authorization_code(
    client: httpx.Client,
    *,
    token_endpoint: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
    code_verifier: str,
) -> dict[str, Any]:
    """Authorization-code exchange; returns token JSON (access_token, refresh_token, …)."""
    fields = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    if client_secret:
        fields["client_secret"] = client_secret
    resp = client.post(
        token_endpoint,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": _DEFAULT_UA,
        },
        data=fields,
        timeout=30.0,
    )
    if not resp.is_success:
        logger.warning("notion_mcp_oauth=token_exchange_failed status=<%s>", resp.status_code)
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        msg = "token response must be a JSON object"
        raise TypeError(msg)
    return cast(dict[str, Any], body)


def refresh_access_token(
    client: httpx.Client,
    *,
    token_endpoint: str,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, Any]:
    """Refresh-token grant; may return a rotated ``refresh_token``."""
    fields = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        fields["client_secret"] = client_secret
    resp = client.post(
        token_endpoint,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": _DEFAULT_UA,
        },
        data=fields,
        timeout=30.0,
    )
    if not resp.is_success:
        logger.warning("notion_mcp_oauth=refresh_failed status=<%s>", resp.status_code)
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        msg = "refresh response must be a JSON object"
        raise TypeError(msg)
    return cast(dict[str, Any], body)


def parse_authorization_callback_url(callback_url: str) -> dict[str, str | None]:
    """Parse ``code``, ``state``, ``error`` from redirect URL query string."""
    parsed = urlparse(callback_url)
    qs = parse_qs(parsed.query)

    def _first(key: str) -> str | None:
        vals = qs.get(key)
        if not vals:
            return None
        return vals[0]

    return {
        "code": _first("code"),
        "state": _first("state"),
        "error": _first("error"),
        "error_description": _first("error_description"),
    }


def token_response_to_store_fields(body: dict[str, Any]) -> dict[str, Any]:
    """Normalize token JSON into numeric ``expires_at`` (``time.time()`` epoch)."""
    access = body.get("access_token")
    if not isinstance(access, str) or not access:
        msg = "token response missing access_token"
        raise ValueError(msg)
    expires_in = body.get("expires_in")
    expires_at: float | None = None
    if isinstance(expires_in, (int, float)):
        expires_at = time.time() + float(expires_in)
    refresh = body.get("refresh_token")
    refresh_out: str | None = None
    if isinstance(refresh, str) and refresh:
        refresh_out = refresh
    return {
        "access_token": access,
        "refresh_token": refresh_out,
        "expires_at": expires_at,
    }
