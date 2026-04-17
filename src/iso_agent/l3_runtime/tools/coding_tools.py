"""Strands coding tools (same stack as SDK personal-assistant sample)."""

from __future__ import annotations

import logging
from typing import Any

from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)


def build_coding_tools(scope: UserScope, *, enabled: bool) -> list[Any]:
    """Return ``python_repl``, ``editor``, ``shell``, and ``journal`` when ``enabled``.

    These tools run with the host process privileges. The Neuuf coordinator passes
    ``enabled=True`` for trusted entry points (CLI, in-process handler); Google Chat passes
    ``enabled=False`` so remote users never get shell or arbitrary file edit.

    Args:
        scope: Per-user scope (reserved for future cwd / path scoping).
        enabled: When false, return an empty list.

    Returns:
        Zero or four tool modules for :class:`~strands.agent.agent.Agent`.
    """
    del scope
    if not enabled:
        return []

    from strands_tools import editor, journal, python_repl, shell

    logger.info("coding_tools=enabled | registering python_repl, editor, shell, journal")
    return [python_repl, editor, shell, journal]
