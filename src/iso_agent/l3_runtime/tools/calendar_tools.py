"""User-scoped calendar tools (Phase 7; local SQLite under ``memory_root/calendar/``)."""

from __future__ import annotations

import json
import logging
from typing import Any

from strands.tools.decorator import tool

from iso_agent.l2_user import calendar_store
from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)


def build_calendar_tools(scope: UserScope) -> list[Any]:
    """Build calendar CRUD tools scoped to this user's memory partition."""

    @tool(
        name="iso_calendar_create",
        description=(
            "Create a personal/audit meeting record in this user's on-disk calendar "
            "(not Google Calendar). date format: YYYY-MM-DD HH:MM."
        ),
    )
    def iso_calendar_create(
        date: str,
        location: str,
        title: str,
        description: str,
    ) -> str:
        """Insert an appointment row; returns appointment id."""
        try:
            aid = calendar_store.calendar_create(
                scope,
                date=date,
                location=location,
                title=title,
                description=description,
            )
        except ValueError as exc:
            logger.debug("user_key=<%s> | calendar create rejected", scope.user_key)
            return f"error: {exc}"
        return f"created appointment_id={aid}"

    @tool(
        name="iso_calendar_list",
        description="List all appointments for this user from the local calendar database.",
    )
    def iso_calendar_list() -> str:
        """Return JSON array of appointment rows."""
        rows = calendar_store.calendar_list_rows(scope)
        out = json.dumps(rows, indent=2)
        logger.debug("user_key=<%s>, count=<%d> | iso_calendar_list", scope.user_key, len(rows))
        return out

    @tool(
        name="iso_calendar_agenda",
        description="Show appointments for one calendar day (YYYY-MM-DD) from the local DB.",
    )
    def iso_calendar_agenda(day: str) -> str:
        """Return JSON for that day's rows."""
        try:
            rows = calendar_store.calendar_agenda_for_day(scope, day=day)
        except ValueError as exc:
            return f"error: {exc}"
        return json.dumps(rows, indent=2)

    @tool(
        name="iso_calendar_update",
        description=(
            "Update an appointment by id. Pass only fields to change; "
            "date format YYYY-MM-DD HH:MM when provided."
        ),
    )
    def iso_calendar_update(
        appointment_id: str,
        date: str = "",
        location: str = "",
        title: str = "",
        description: str = "",
    ) -> str:
        """Patch fields; empty strings mean leave unchanged."""
        try:
            n = calendar_store.calendar_update(
                scope,
                appointment_id=appointment_id,
                date=date or None,
                location=location or None,
                title=title or None,
                description=description or None,
            )
        except ValueError as exc:
            return f"error: {exc}"
        if n == 0:
            return "error: no matching appointment_id or no fields to update"
        return f"updated appointment_id={appointment_id}"

    return [iso_calendar_create, iso_calendar_list, iso_calendar_agenda, iso_calendar_update]
