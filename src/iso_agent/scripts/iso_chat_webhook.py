"""Run the Google Chat webhook HTTP server (uvicorn)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Listen on ``PORT`` (default 8080) for ``POST /google-chat``."""
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "iso_agent.adapters.google_chat_app:app",
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("UVICORN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
