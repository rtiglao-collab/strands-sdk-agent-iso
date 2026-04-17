"""Audit cadence tools: schedule file under ``memory_root/audits/`` (Phase 7)."""

from __future__ import annotations

import json
import logging
from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user import audit_schedule
from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)


def build_audit_tools(scope: UserScope) -> list[Any]:
    """Build audit reminder / schedule tools for this user scope."""

    @tool(
        name="audit_schedule_add",
        description=(
            "Add a recurring audit or management review obligation. "
            "audit_type: internal | external | management_review | other. "
            "cadence_days: 1–366. Use audit_mark_completed after each run to advance due dates."
        ),
    )
    def audit_schedule_add(label: str, cadence_days: int, audit_type: str) -> str:
        """Persist one schedule row; returns schedule_id."""
        try:
            item = audit_schedule.schedule_add(
                scope,
                label=label,
                cadence_days=cadence_days,
                audit_type=audit_type,
            )
        except ValueError as exc:
            return f"error: {exc}"
        return f"saved schedule_id={item.schedule_id} audit_type={item.audit_type}"

    @tool(
        name="audit_schedule_list",
        description="Return JSON of all audit schedule rows for this user.",
    )
    def audit_schedule_list() -> str:
        """JSON list of schedule items."""
        items = audit_schedule.load_schedule(scope)
        out = json.dumps([i.model_dump() for i in items], indent=2)
        logger.debug("user_key=<%s>, count=<%d> | audit_schedule_list", scope.user_key, len(items))
        return out

    @tool(
        name="audit_mark_completed",
        description=(
            "Record that an audit schedule row was completed. "
            "completed_date optional YYYY-MM-DD (default: today)."
        ),
    )
    def audit_mark_completed(schedule_id: str, completed_date: str = "") -> str:
        """Set last_completed_iso for one schedule_id."""
        ok = audit_schedule.mark_completed(
            scope,
            schedule_id=schedule_id,
            completed_day=completed_date or None,
        )
        if not ok:
            return f"error: unknown schedule_id={schedule_id}"
        return f"marked completed schedule_id={schedule_id}"

    @tool(
        name="audit_upcoming_reminders",
        description=(
            "List audits due within N days or overdue, based on last completion + cadence. "
            "Requires audit_mark_completed to establish baselines."
        ),
    )
    def audit_upcoming_reminders(within_days: int = 30) -> str:
        """Plain-text lines suitable for neuuf_comms follow-up."""
        lines = audit_schedule.upcoming_lines(scope, within_days=within_days)
        if not lines:
            return "no scheduled audits in file — add rows with audit_schedule_add"
        return "\n".join(lines)

    return [
        audit_schedule_add,
        audit_schedule_list,
        audit_mark_completed,
        audit_upcoming_reminders,
    ]
