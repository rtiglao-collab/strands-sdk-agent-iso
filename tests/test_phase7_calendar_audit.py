"""Tests for Phase 7 local calendar and audit cadence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iso_agent.l2_user import audit_schedule, calendar_store
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.tools.audit_tools import build_audit_tools
from iso_agent.l3_runtime.tools.calendar_tools import build_calendar_tools


def _scope(tmp_path: Path) -> UserScope:
    root = tmp_path / "u1"
    root.mkdir(parents=True)
    return UserScope(user_key="u1", memory_root=root, thread_key="u1|s|t")


def test_calendar_create_list_agenda(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    aid = calendar_store.calendar_create(
        scope,
        date="2026-03-10 14:00",
        location="Room A",
        title="Internal audit closeout",
        description="Review findings",
    )
    rows = calendar_store.calendar_list_rows(scope)
    assert len(rows) == 1
    assert rows[0]["id"] == aid
    day = calendar_store.calendar_agenda_for_day(scope, day="2026-03-10")
    assert len(day) == 1
    assert day[0]["title"] == "Internal audit closeout"


def test_calendar_invalid_date(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    with pytest.raises(ValueError):
        calendar_store.calendar_create(
            scope,
            date="not-a-date",
            location="x",
            title="t",
            description="d",
        )


def test_calendar_update(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    aid = calendar_store.calendar_create(
        scope,
        date="2026-04-01 09:00",
        location="HQ",
        title="Mgmt review",
        description="Q1",
    )
    n = calendar_store.calendar_update(
        scope,
        appointment_id=aid,
        title="Mgmt review (updated)",
    )
    assert n == 1
    rows = calendar_store.calendar_list_rows(scope)
    assert rows[0]["title"] == "Mgmt review (updated)"


def test_audit_schedule_roundtrip(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    item = audit_schedule.schedule_add(
        scope,
        label="Internal QMS audit",
        cadence_days=365,
        audit_type="internal",
    )
    items = audit_schedule.load_schedule(scope)
    assert len(items) == 1
    assert items[0].schedule_id == item.schedule_id


def test_audit_upcoming_overdue(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    item = audit_schedule.schedule_add(
        scope,
        label="External supplier audit",
        cadence_days=90,
        audit_type="external",
    )
    assert audit_schedule.mark_completed(
        scope,
        schedule_id=item.schedule_id,
        completed_day="2020-01-01",
    )
    lines = audit_schedule.upcoming_lines(scope, within_days=30)
    assert len(lines) == 1
    assert "OVERDUE" in lines[0]


def test_audit_no_baseline_line(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    audit_schedule.schedule_add(
        scope,
        label="New obligation",
        cadence_days=30,
        audit_type="management_review",
    )
    lines = audit_schedule.upcoming_lines(scope, within_days=90)
    assert len(lines) == 1
    assert "no completion baseline" in lines[0]


def test_calendar_tools_build(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    tools = build_calendar_tools(scope)
    assert len(tools) == 4
    create, list_t, agenda, update = tools
    r = str(
        create(
            date="2026-05-01 10:00",
            location="Virtual",
            title="T",
            description="D",
        )
    )
    assert "appointment_id=" in r
    arr = json.loads(str(list_t()))
    assert len(arr) == 1


def test_audit_tools_build(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    tools = build_audit_tools(scope)
    assert len(tools) == 4
    add, list_t, mark, upcoming = tools
    r = str(add("Label A", 180, "internal"))
    assert "schedule_id=" in r
    data = json.loads(str(list_t()))
    sid = data[0]["schedule_id"]
    assert "marked completed" in str(mark(sid, "2026-01-15"))
