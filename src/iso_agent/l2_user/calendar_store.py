"""Per-user SQLite calendar (Phase 7; pattern from Strands ``05-personal-assistant``)."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from iso_agent.l2_user.user_scope import UserScope

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    location TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL
);
"""


def _db_path(scope: UserScope) -> Path:
    d = scope.memory_root / "calendar"
    d.mkdir(parents=True, exist_ok=True)
    return d / "appointments.db"


def _connect(scope: UserScope) -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path(scope)))
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def calendar_create(
    scope: UserScope,
    *,
    date: str,
    location: str,
    title: str,
    description: str,
) -> str:
    """Insert one appointment; ``date`` must be ``YYYY-MM-DD HH:MM``."""
    datetime.strptime(date, "%Y-%m-%d %H:%M")
    aid = str(uuid.uuid4())
    with _connect(scope) as conn:
        conn.execute(
            "INSERT INTO appointments (id, date, location, title, description) VALUES (?,?,?,?,?)",
            (aid, date, location, title, description),
        )
        conn.commit()
    logger.debug("appointment_id=<%s>, user_key=<%s> | calendar row inserted", aid, scope.user_key)
    return aid


def calendar_list_rows(scope: UserScope) -> list[dict[str, Any]]:
    """Return all appointments ordered by ``date`` ascending."""
    with _connect(scope) as conn:
        cur = conn.execute(
            "SELECT id, date, location, title, description FROM appointments ORDER BY date"
        )
        desc = cur.description
        if desc is None:
            return []
        cols = [d[0] for d in desc]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def calendar_agenda_for_day(scope: UserScope, *, day: str) -> list[dict[str, Any]]:
    """Return appointments whose ``date`` starts with ``day`` (``YYYY-MM-DD``)."""
    datetime.strptime(day, "%Y-%m-%d")
    with _connect(scope) as conn:
        cur = conn.execute(
            "SELECT id, date, location, title, description FROM appointments "
            "WHERE date LIKE ? ORDER BY date",
            (f"{day}%",),
        )
        desc = cur.description
        if desc is None:
            return []
        cols = [d[0] for d in desc]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def calendar_update(
    scope: UserScope,
    *,
    appointment_id: str,
    date: str | None = None,
    location: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> int:
    """Update non-``None`` fields; returns number of rows updated (0 or 1)."""
    if date is not None:
        datetime.strptime(date, "%Y-%m-%d %H:%M")
    fields: list[str] = []
    params: list[Any] = []
    if date is not None:
        fields.append("date = ?")
        params.append(date)
    if location is not None:
        fields.append("location = ?")
        params.append(location)
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if not fields:
        return 0
    params.append(appointment_id)
    sql = f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?"
    with _connect(scope) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        updated = cur.rowcount
    logger.debug(
        "appointment_id=<%s>, user_key=<%s>, fields=<%d> | calendar row updated",
        appointment_id,
        scope.user_key,
        len(fields),
    )
    return int(updated)
