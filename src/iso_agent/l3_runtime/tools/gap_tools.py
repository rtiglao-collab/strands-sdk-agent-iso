"""Coordinator tools for persisting and listing QMS gap records (Phase 6)."""

from __future__ import annotations

import logging
from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user.gap_store import append_gap_record, recent_gaps_json
from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)

_MAX_TOOL_LIST = 50


def build_gap_tools(scope: UserScope) -> list[Any]:
    """Build gap pipeline tools (always scoped to ``scope.memory_root``)."""

    @tool(
        name="gap_append_record",
        description=(
            "Append one structured gap record to the user's append-only gaps log "
            "(memory/users/<user_key>/gaps/gaps.jsonl). Use after neuuf_gap_analyst "
            "when the user wants persistence. severity: low | medium | high."
        ),
    )
    def gap_append_record(
        title: str,
        summary: str,
        severity: str,
        suggested_owner_role: str,
        iso_clause_refs: str = "",
        evidence_refs: str = "",
    ) -> str:
        """Persist a single gap row; returns gap_id or an error string."""
        try:
            rec = append_gap_record(
                scope,
                title=title,
                summary=summary,
                severity=severity,
                suggested_owner_role=suggested_owner_role,
                iso_clause_refs=iso_clause_refs,
                evidence_refs=evidence_refs,
            )
        except ValueError as exc:
            logger.debug("gap_append_failed user_key=<%s> | %s", scope.user_key, exc)
            return f"error: {exc}"
        return (
            f"saved gap_id={rec.gap_id} created_at={rec.created_at} "
            f"(append-only log under gaps/gaps.jsonl)"
        )

    @tool(
        name="gap_list_recent",
        description=(
            "List recent gap records (JSON) for drafting owner follow-up via neuuf_comms "
            "or Notion. Reads only this user's gaps log."
        ),
    )
    def gap_list_recent(limit: int = 10) -> str:
        """Return JSON text of the last N gap records (newest at end of array)."""
        lim = max(1, min(int(limit), _MAX_TOOL_LIST))
        out = recent_gaps_json(scope, limit=lim)
        logger.debug(
            "user_key=<%s>, limit=<%d> | gap_list_recent returned",
            scope.user_key,
            lim,
        )
        return out

    return [gap_append_record, gap_list_recent]
