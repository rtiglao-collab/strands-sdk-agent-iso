"""Notion hosted MCP — per-user OAuth store + Strands :class:`~strands.tools.mcp.MCPClient`.

See `docs/NOTION_MCP.md` for transport modes and the REST vs MCP parity checklist.
"""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
import webbrowser
from collections.abc import Callable
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

from iso_agent.config import get_settings
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_mcp_oauth as oauth

logger = logging.getLogger(__name__)

_OAUTH_FILENAME = "mcp_oauth.json"
_SKEW_SECONDS = 120.0
# If the authorization server omits ``expires_in``, assume this TTL so we do not call
# ``refresh_token`` on every ``ensure_notion_mcp_client`` (which can fail intermittently
# and previously dropped all Notion tools by returning ``None``).
_ASSUMED_ACCESS_TOKEN_TTL_SECONDS = 3600.0

_clients: dict[str, MCPClient] = {}
_client_lock = threading.Lock()
_last_access_token: dict[str, str] = {}
_reload_lock = threading.Lock()
_pending_coordinator_reload_after_oauth = False


def notion_mcp_oauth_store_path(scope: UserScope) -> Path:
    """Path to persisted OAuth tokens (never log contents)."""
    d = scope.memory_root / "notion"
    return d / _OAUTH_FILENAME


def notion_mcp_oauth_configured(scope: UserScope) -> bool:
    """Return True when ``mcp_oauth.json`` exists for this user."""
    return notion_mcp_oauth_store_path(scope).is_file()


def _load_store(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        msg = "oauth store must be a JSON object"
        raise TypeError(msg)
    return data


def _save_store(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _refresh_store_sync(path: Path, store: dict[str, Any]) -> dict[str, Any]:
    """Refresh access token using ``refresh_token``; mutates and saves ``store``."""
    rt = store.get("refresh_token")
    cid = store.get("client_id")
    tep = store.get("token_endpoint")
    if not isinstance(rt, str) or not rt:
        msg = "cannot refresh: missing refresh_token"
        raise ValueError(msg)
    if not isinstance(cid, str) or not cid:
        msg = "cannot refresh: missing client_id"
        raise ValueError(msg)
    if not isinstance(tep, str) or not tep:
        msg = "cannot refresh: missing token_endpoint"
        raise ValueError(msg)
    secret = store.get("client_secret")
    sec: str | None = secret if isinstance(secret, str) else None
    with httpx.Client() as client:
        body = oauth.refresh_access_token(
            client,
            token_endpoint=tep,
            refresh_token=rt,
            client_id=cid,
            client_secret=sec,
        )
    fields = oauth.token_response_to_store_fields(body)
    store["access_token"] = fields["access_token"]
    if fields.get("refresh_token"):
        store["refresh_token"] = fields["refresh_token"]
    if fields.get("expires_at") is not None:
        store["expires_at"] = fields["expires_at"]
    _save_store(path, store)
    return store


def ensure_fresh_oauth_store(scope: UserScope) -> dict[str, Any] | None:
    """Load ``mcp_oauth.json`` and refresh the access token when near expiry.

    Refresh failures fall back to the last known ``access_token`` so a transient
    network error does not remove Notion tools until the token is actually invalid
    (MCP calls may fail until refresh succeeds). Stores without ``expires_at`` get
    a synthetic value so we do not invoke ``refresh_token`` on every client startup.
    """
    path = notion_mcp_oauth_store_path(scope)
    if not path.is_file():
        return None
    try:
        store = _load_store(path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning(
            "notion_mcp=store_read_failed exc_type=<%s>",
            type(exc).__name__,
            exc_info=exc,
        )
        return None
    now = time.time()
    exp = store.get("expires_at")
    if not isinstance(exp, (int, float)):
        try:
            store["expires_at"] = now + _ASSUMED_ACCESS_TOKEN_TTL_SECONDS
            _save_store(path, store)
        except OSError as exc:
            logger.warning(
                "notion_mcp=expires_bootstrap_write_failed exc_type=<%s>",
                type(exc).__name__,
                exc_info=exc,
            )
        exp = store.get("expires_at")

    needs = isinstance(exp, (int, float)) and float(exp) - _SKEW_SECONDS <= now
    if needs:
        try:
            store = _refresh_store_sync(path, store)
        except Exception as exc:
            logger.warning(
                "notion_mcp=refresh_failed exc_type=<%s> | using_stale_access_token",
                type(exc).__name__,
                exc_info=exc,
            )
            access = store.get("access_token")
            if isinstance(access, str) and access:
                return store
            return None
    return store


def _mcp_should_register() -> bool:
    s = get_settings()
    return s.notion_transport in ("hybrid", "mcp_primary")


def _shutdown_client(user_key: str) -> None:
    global _clients, _last_access_token
    c = _clients.pop(user_key, None)
    _last_access_token.pop(user_key, None)
    if c is None:
        return
    try:
        c.__exit__(None, None, None)  # type: ignore[arg-type]
    except Exception as exc:
        logger.debug("notion_mcp=shutdown_note exc_type=<%s>", type(exc).__name__, exc_info=exc)


def _shutdown_all_notion_mcp_clients() -> None:
    keys = list(_clients.keys())
    for k in keys:
        _shutdown_client(k)


def request_coordinator_reload_after_notion_mcp_oauth() -> None:
    """Signal the CLI host to rebuild the coordinator so new MCP tools load."""
    global _pending_coordinator_reload_after_oauth
    with _reload_lock:
        _pending_coordinator_reload_after_oauth = True


def consume_coordinator_reload_after_notion_mcp_oauth() -> bool:
    """Return True once if the host should rebuild the :class:`~strands.agent.agent.Agent`."""
    global _pending_coordinator_reload_after_oauth
    with _reload_lock:
        if not _pending_coordinator_reload_after_oauth:
            return False
        _pending_coordinator_reload_after_oauth = False
        return True


def reset_notion_mcp_for_tests() -> None:
    """Close all cached Notion MCP clients (tests only)."""
    with _client_lock:
        _shutdown_all_notion_mcp_clients()


def _atexit_shutdown() -> None:
    if _clients:
        reset_notion_mcp_for_tests()


atexit.register(_atexit_shutdown)


def _transport_callable(access_token: str, mcp_url: str) -> Callable[[], Any]:
    @asynccontextmanager
    async def _cm() -> Any:

        timeout = httpx.Timeout(60.0, read=300.0)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "iso-agent-notion-mcp/0.1",
        }
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as http_client:
            async with streamable_http_client(mcp_url, http_client=http_client) as streams:
                yield streams

    return lambda: _cm()


def ensure_notion_mcp_client(scope: UserScope) -> MCPClient | None:
    """Return a started :class:`~strands.tools.mcp.MCPClient` for this user, or ``None``."""
    if not _mcp_should_register():
        return None
    store = ensure_fresh_oauth_store(scope)
    if store is None:
        return None
    access = store.get("access_token")
    if not isinstance(access, str) or not access:
        return None
    s = get_settings()
    mcp_url = s.notion_mcp_url.strip()
    user_key = scope.user_key
    global _clients, _last_access_token
    with _client_lock:
        prev = _last_access_token.get(user_key)
        if prev != access and user_key in _clients:
            _shutdown_client(user_key)
        _last_access_token[user_key] = access
        if user_key not in _clients:
            try:
                _clients[user_key] = MCPClient(
                    _transport_callable(access, mcp_url),
                    prefix="notion_mcp_",
                )
                _clients[user_key].__enter__()
                tools = _clients[user_key].list_tools_sync()
            except Exception as exc:
                logger.warning(
                    "notion_mcp=startup_failed exc_type=<%s>",
                    type(exc).__name__,
                    exc_info=exc,
                )
                _shutdown_client(user_key)
                return None
            logger.info("notion_mcp=ready user_key=<%s> tool_count=<%d>", user_key, len(tools))
            return _clients[user_key]
        return _clients[user_key]


def get_notion_mcp_tools(scope: UserScope) -> list[Any] | None:
    """Return raw Notion MCP tool adapters (optional); prefer ``ensure_notion_mcp_client``."""
    client = ensure_notion_mcp_client(scope)
    if client is None:
        return None
    return list(client.list_tools_sync())


def run_notion_mcp_interactive_login(scope: UserScope, *, open_browser: bool = True) -> None:
    """OAuth browser login: dynamic client registration, localhost callback, token file write."""
    import secrets as sec_mod

    settings = get_settings()
    notion_dir = scope.memory_root / "notion"
    notion_dir.mkdir(parents=True, exist_ok=True)
    out_path = notion_mcp_oauth_store_path(scope)

    redirect_uri = settings.notion_mcp_redirect_uri.strip()
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    callback_path = parsed.path or "/callback"

    captured: list[str | None] = [None]

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, _fmt: str, *_args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            req_path = self.path.split("?", 1)[0]
            if req_path != callback_path.rstrip("/") and req_path != callback_path:
                self.send_error(404)
                return
            captured[0] = f"{parsed.scheme}://{host}:{port}{self.path}"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Notion MCP login complete. You can close this tab and return to the terminal."
            )

    with httpx.Client() as http:
        meta = oauth.discover_oauth_endpoints(http, mcp_url=settings.notion_mcp_url)
        auth_ep = meta.get("authorization_endpoint")
        token_ep = meta.get("token_endpoint")
        reg_ep = meta.get("registration_endpoint")
        if not isinstance(auth_ep, str) or not isinstance(token_ep, str):
            msg = "authorization server metadata missing endpoints"
            raise ValueError(msg)
        if not isinstance(reg_ep, str) or not reg_ep:
            msg = "dynamic client registration is required but registration_endpoint missing"
            raise ValueError(msg)

        client_id, client_secret = oauth.register_public_client(
            http, registration_endpoint=reg_ep, redirect_uri=redirect_uri
        )
        verifier, challenge = oauth.generate_pkce_pair()
        state = sec_mod.token_urlsafe(24)
        auth_url = oauth.build_authorization_url(
            authorization_endpoint=auth_ep,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=challenge,
            state=state,
        )

    server = HTTPServer((host, port), _Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    print("Open this URL in a browser (if it did not open automatically):")
    print(auth_url)
    if open_browser:
        webbrowser.open(auth_url)
    deadline = time.time() + 600.0
    while captured[0] is None and time.time() < deadline:
        time.sleep(0.15)
    server.shutdown()
    server.server_close()
    th.join(timeout=5.0)

    cb = captured[0]
    if not cb:
        raise SystemExit("Timed out waiting for OAuth redirect (10 minutes).")

    parts = oauth.parse_authorization_callback_url(cb)
    if parts.get("error"):
        desc = parts.get("error_description") or ""
        raise SystemExit(f"OAuth error: {parts.get('error')} — {desc}")
    if parts.get("state") != state:
        raise SystemExit("OAuth state mismatch — aborting.")
    code = parts.get("code")
    if not code:
        raise SystemExit("Missing authorization code in callback.")

    with httpx.Client() as http:
        token_body = oauth.exchange_authorization_code(
            http,
            token_endpoint=token_ep,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
            code_verifier=verifier,
        )

    fields = oauth.token_response_to_store_fields(token_body)
    store: dict[str, Any] = {
        "mcp_streamable_url": settings.notion_mcp_url.strip(),
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "token_endpoint": token_ep,
        "authorization_endpoint": auth_ep,
        "registration_endpoint": reg_ep,
        "access_token": fields["access_token"],
        "expires_at": fields.get("expires_at"),
    }
    if client_secret:
        store["client_secret"] = client_secret
    if fields.get("refresh_token"):
        store["refresh_token"] = fields["refresh_token"]

    _save_store(out_path, store)
    reset_notion_mcp_for_tests()
    print(f"Saved Notion MCP OAuth tokens to {out_path} (do not commit this file).")


def build_notion_mcp_oauth_tool(scope: UserScope) -> list[Any]:
    """Single coordinator tool to run browser OAuth without a separate CLI (local REPL)."""
    if not _mcp_should_register():
        return []
    from strands.tools.decorator import tool

    @tool(
        name="notion_mcp_oauth_interactive_login",
        description=(
            "One-time (or rare) Notion hosted MCP browser OAuth; saves tokens under memory/.../notion/. "
            "After success the REPL reloads the coordinator so **notion_*** QMS tools run. Tokens "
            "refresh automatically; call this only for first setup, revoked access, or a new "
            "Notion account/workspace."
        ),
    )
    def notion_mcp_oauth_interactive_login() -> str:
        try:
            run_notion_mcp_interactive_login(scope, open_browser=True)
        except SystemExit as exc:
            return f"error=oauth_failed detail={exc!s}"
        except Exception as exc:
            logger.warning(
                "notion_mcp=oauth_tool_failed exc_type=<%s>",
                type(exc).__name__,
                exc_info=exc,
            )
            return f"error=oauth_failed exc_type={type(exc).__name__}"
        request_coordinator_reload_after_notion_mcp_oauth()
        return (
            "ok=notion_mcp_oauth_saved | OAuth finished. The CLI reloads the coordinator after "
            "this turn; then **notion_*** tools use hosted Notion MCP."
        )

    return [notion_mcp_oauth_interactive_login]
