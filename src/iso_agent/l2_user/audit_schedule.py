"""On-disk audit cadence schedule per user (Phase 7)."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)

AuditType = Literal["internal", "external", "management_review", "other"]


class AuditScheduleItem(BaseModel):
    """One recurring audit / review obligation for a user scope."""

    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    label: str = Field(min_length=1, max_length=200)
    cadence_days: int = Field(ge=1, le=366)
    audit_type: AuditType
    last_completed_iso: str | None = None

    @field_validator("last_completed_iso")
    @classmethod
    def _validate_last(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        date.fromisoformat(v[:10])
        return v[:10]


def _schedule_path(scope: UserScope) -> Path:
    d = scope.memory_root / "audits"
    d.mkdir(parents=True, exist_ok=True)
    return d / "schedule.json"


def load_schedule(scope: UserScope) -> list[AuditScheduleItem]:
    path = _schedule_path(scope)
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    out: list[AuditScheduleItem] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(AuditScheduleItem.model_validate(item))
    return out


def _parse_audit_type(raw: str) -> AuditType:
    at = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if at in {"mgmt", "management"}:
        at = "management_review"
    if at not in {"internal", "external", "management_review", "other"}:
        raise ValueError(
            "audit_type must be internal, external, management_review, or other",
        )
    return cast(AuditType, at)


def save_schedule(scope: UserScope, items: list[AuditScheduleItem]) -> None:
    path = _schedule_path(scope)
    path.write_text(
        json.dumps([i.model_dump() for i in items], indent=2),
        encoding="utf-8",
    )
    logger.debug("user_key=<%s>, count=<%d> | audit schedule saved", scope.user_key, len(items))


def schedule_add(
    scope: UserScope,
    *,
    label: str,
    cadence_days: int,
    audit_type: str,
) -> AuditScheduleItem:
    """Append a new schedule row."""
    normalized = _parse_audit_type(audit_type)
    try:
        item = AuditScheduleItem(
            schedule_id=str(uuid4()),
            label=label.strip(),
            cadence_days=cadence_days,
            audit_type=normalized,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    items = load_schedule(scope)
    items.append(item)
    save_schedule(scope, items)
    logger.debug(
        "schedule_id=<%s>, user_key=<%s>, audit_type=<%s> | audit schedule row added",
        item.schedule_id,
        scope.user_key,
        item.audit_type,
    )
    return item


def mark_completed(scope: UserScope, *, schedule_id: str, completed_day: str | None) -> bool:
    """Set ``last_completed_iso`` to ``completed_day`` (``YYYY-MM-DD``) or today UTC date."""
    if completed_day:
        day = date.fromisoformat(completed_day[:10])
    else:
        day = date.today()
    iso = day.isoformat()
    items = load_schedule(scope)
    found = False
    for i, it in enumerate(items):
        if it.schedule_id == schedule_id:
            items[i] = it.model_copy(update={"last_completed_iso": iso})
            found = True
            break
    if not found:
        return False
    save_schedule(scope, items)
    logger.debug("schedule_id=<%s>, day=<%s> | audit marked completed", schedule_id, iso)
    return True


def next_due_date(item: AuditScheduleItem) -> date | None:
    """Next due date from last completion + cadence, or ``None`` if never completed."""
    if not item.last_completed_iso:
        return None
    base = date.fromisoformat(item.last_completed_iso[:10])
    return base + timedelta(days=item.cadence_days)


def upcoming_lines(scope: UserScope, *, within_days: int) -> list[str]:
    """Human-readable lines for audits due within ``within_days`` or overdue."""
    cap = max(1, min(int(within_days), 366))
    today = date.today()
    horizon = today + timedelta(days=cap)
    lines: list[str] = []
    for it in load_schedule(scope):
        nd = next_due_date(it)
        if nd is None:
            lines.append(
                f"{it.label} ({it.audit_type}): no completion baseline — "
                f"set via audit_mark_completed after first run",
            )
            continue
        if nd < today:
            lines.append(
                f"{it.label} ({it.audit_type}): OVERDUE since {nd.isoformat()} "
                f"(cadence {it.cadence_days}d, id={it.schedule_id})",
            )
        elif nd <= horizon:
            lines.append(
                f"{it.label} ({it.audit_type}): due {nd.isoformat()} "
                f"(cadence {it.cadence_days}d, id={it.schedule_id})",
            )
    return lines
