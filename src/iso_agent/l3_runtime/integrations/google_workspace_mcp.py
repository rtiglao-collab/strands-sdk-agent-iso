"""Google Workspace MCP (stdio via npx) — optional coordinator tools.

Spawns ``npx -y google-workspace-mcp serve`` (with ``--read-only`` by default).
Requires Node/npm on ``PATH`` and prior ``npx google-workspace-mcp setup`` so
OAuth tokens live under the user home directory (see ``docs/INTEGRATIONS_WALKTHROUGH.md``).
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from typing import Any

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from iso_agent.config import get_settings

logger = logging.getLogger(__name__)

_client: MCPClient | None = None
_client_lock = threading.Lock()


def google_workspace_mcp_configured() -> bool:
    """Return True when settings request starting the Google Workspace MCP client."""
    return get_settings().google_workspace_mcp_transport == "stdio"


def _serve_args() -> list[str]:
    s = get_settings()
    args = ["-y", "google-workspace-mcp", "serve"]
    if s.google_workspace_mcp_serve_read_only:
        args.append("--read-only")
    return args


def get_google_workspace_mcp_tools() -> list[Any] | None:
    """Return Google Workspace MCP tools, or ``None`` when transport is disabled."""
    if not google_workspace_mcp_configured():
        return None

    global _client
    with _client_lock:
        if _client is None:
            try:
                _client = MCPClient(
                    lambda: stdio_client(
                        StdioServerParameters(
                            command="npx",
                            args=_serve_args(),
                            env=os.environ.copy(),
                        )
                    ),
                    prefix="google_workspace_mcp_",
                )
                _client.__enter__()
                tools = _client.list_tools_sync()
            except Exception as exc:
                logger.warning(
                    "google_workspace_mcp=startup_failed exc_type=<%s>",
                    type(exc).__name__,
                    exc_info=exc,
                )
                _client = None
                return None
            logger.info("google_workspace_mcp=ready tool_count=<%d>", len(tools))
            return list(tools)
        return list(_client.list_tools_sync())


def _shutdown_google_workspace_client() -> None:
    global _client
    if _client is None:
        return
    try:
        _client.__exit__(None, None, None)  # type: ignore[arg-type]
    except Exception as exc:
        logger.debug(
            "google_workspace_mcp=shutdown_note exc_type=<%s>",
            type(exc).__name__,
            exc_info=exc,
        )
    finally:
        _client = None


def reset_google_workspace_mcp_for_tests() -> None:
    """Tear down the singleton MCP client (tests only)."""
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.__exit__(None, None, None)  # type: ignore[arg-type]
            except Exception:
                pass
            _client = None


atexit.register(_shutdown_google_workspace_client)
