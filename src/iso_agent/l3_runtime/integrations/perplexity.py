"""Perplexity MCP (Docker) — Phase 2 research backend.

Pattern follows ``samples/02-samples/05-personal-assistant/search_assistant.py``.
Requires ``PERPLEXITY_API_KEY`` and ``ISO_AGENT_PERPLEXITY_TRANSPORT=docker``.
Never log the API key value.
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


def _perplexity_api_key() -> str | None:
    raw = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    return raw or None


def perplexity_mcp_configured() -> bool:
    """Return True when env and settings allow starting the Perplexity MCP client."""
    if get_settings().perplexity_transport != "docker":
        return False
    return _perplexity_api_key() is not None


def get_perplexity_mcp_tools() -> list[Any] | None:
    """Return Perplexity MCP tools, or ``None`` for model-only research."""
    if not perplexity_mcp_configured():
        return None
    key = _perplexity_api_key()
    if key is None:
        return None

    global _client
    with _client_lock:
        if _client is None:
            try:
                _client = MCPClient(
                    lambda: stdio_client(
                        StdioServerParameters(
                            command="docker",
                            args=[
                                "run",
                                "-i",
                                "--rm",
                                "-e",
                                "PERPLEXITY_API_KEY",
                                "mcp/perplexity-ask",
                            ],
                            env={"PERPLEXITY_API_KEY": key},
                        )
                    )
                )
                _client.__enter__()
                tools = _client.list_tools_sync()
            except Exception as exc:
                logger.warning(
                    "perplexity_mcp=startup_failed exc_type=<%s> | model_only_researcher",
                    type(exc).__name__,
                    exc_info=exc,
                )
                _client = None
                return None
            logger.info("perplexity_mcp=ready tool_count=<%d>", len(tools))
            return list(tools)
        return list(_client.list_tools_sync())


def _shutdown_perplexity_client() -> None:
    global _client
    if _client is None:
        return
    try:
        _client.__exit__(None, None, None)  # type: ignore[arg-type]
    except Exception as exc:
        logger.debug("perplexity_mcp=shutdown_note exc_type=<%s>", type(exc).__name__, exc_info=exc)
    finally:
        _client = None


def reset_perplexity_mcp_for_tests() -> None:
    """Tear down the singleton MCP client (tests only)."""
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.__exit__(None, None, None)  # type: ignore[arg-type]
            except Exception:
                pass
            _client = None


atexit.register(_shutdown_perplexity_client)
