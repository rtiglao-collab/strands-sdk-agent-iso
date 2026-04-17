"""Append-only gap records under ``memory/users/<user_key>/gaps/`` (Phase 6)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)

_GAP_JSONL = "gaps.jsonl"
_MAX_SUMMARY = 8000
_MAX_TITLE = 200
_MAX_LIST = 50


class GapRecord(BaseModel):
    """One gap hypothesis persisted as a single JSON line in ``gaps.jsonl``."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    created_at: str
    title: str = Field(min_length=1, max_length=_MAX_TITLE)
    summary: str = Field(min_length=1, max_length=_MAX_SUMMARY)
    severity: Literal["low", "medium", "high"]
    suggested_owner_role: str = Field(min_length=1, max_length=300)
    iso_clause_refs: str = Field(default="", max_length=500)
    evidence_refs: str = Field(default="", max_length=500)
    thread_key: str = Field(default="", max_length=500)

    @field_validator("title", "summary", "suggested_owner_role", mode="before")
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


def gaps_directory(scope: UserScope) -> Path:
    """Return ``memory_root/gaps``, creating it if needed."""
    d = scope.memory_root / "gaps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def gaps_jsonl_path(scope: UserScope) -> Path:
    """Path to the append-only JSONL log for this user."""
    return gaps_directory(scope) / _GAP_JSONL


def _normalize_severity(raw: str) -> Literal["low", "medium", "high"]:
    s = raw.strip().lower()
    if s in {"med", "mid"}:
        s = "medium"
    if s not in {"low", "medium", "high"}:
        raise ValueError("severity must be one of: low, medium, high")
    return s  # type: ignore[return-value]


def append_gap_record(
    scope: UserScope,
    *,
    title: str,
    summary: str,
    severity: str,
    suggested_owner_role: str,
    iso_clause_refs: str = "",
    evidence_refs: str = "",
) -> GapRecord:
    """Append one validated :class:`GapRecord` and return it (including ``gap_id``)."""
    gap_id = str(uuid4())
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        sev = _normalize_severity(severity)
        record = GapRecord(
            gap_id=gap_id,
            created_at=created_at,
            title=title,
            summary=summary,
            severity=sev,
            suggested_owner_role=suggested_owner_role,
            iso_clause_refs=iso_clause_refs.strip(),
            evidence_refs=evidence_refs.strip(),
            thread_key=scope.thread_key,
        )
    except (ValueError, ValidationError) as exc:
        raise ValueError(str(exc)) from exc
    path = gaps_jsonl_path(scope)
    line = record.model_dump_json() + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    logger.debug(
        "gap_id=<%s>, user_key=<%s>, severity=<%s> | gap record appended",
        gap_id,
        scope.user_key,
        sev,
    )
    return record


def list_recent_gaps(scope: UserScope, *, limit: int = 10) -> list[GapRecord]:
    """Return the last ``limit`` records from ``gaps.jsonl`` (oldest-first within the window)."""
    capped = max(1, min(int(limit), _MAX_LIST))
    path = gaps_jsonl_path(scope)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-capped:] if capped else []
    out: list[GapRecord] = []
    for line in tail:
        if not line.strip():
            continue
        try:
            out.append(GapRecord.model_validate_json(line))
        except Exception:
            logger.warning(
                "user_key=<%s>, line_len=<%d> | gap jsonl line skipped (parse error)",
                scope.user_key,
                len(line),
            )
    return out


def recent_gaps_json(scope: UserScope, *, limit: int = 10) -> str:
    """JSON array of recent gaps for tools / comms handoff."""
    rows = [r.model_dump() for r in list_recent_gaps(scope, limit=limit)]
    return json.dumps(rows, indent=2)
