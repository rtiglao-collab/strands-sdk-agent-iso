"""Tests for Phase 6 gap JSONL store."""

from __future__ import annotations

from pathlib import Path

import pytest

from iso_agent.l2_user.gap_store import (
    GapRecord,
    append_gap_record,
    gaps_jsonl_path,
    list_recent_gaps,
)
from iso_agent.l2_user.user_scope import UserScope


def _scope(tmp_path: Path) -> UserScope:
    root = tmp_path / "uk1"
    root.mkdir(parents=True)
    return UserScope(
        user_key="uk1",
        memory_root=root,
        thread_key="uk1|space|thread1",
    )


def test_append_and_list_roundtrip(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    a = append_gap_record(
        scope,
        title="Missing calibration log",
        summary="Process X has no dated entries for Q2.",
        severity="high",
        suggested_owner_role="Quality manager",
        iso_clause_refs="7.1.5",
        evidence_refs="drive:folderABC/file123",
    )
    b = append_gap_record(
        scope,
        title="Training matrix stale",
        summary="Three roles show expired training.",
        severity="medium",
        suggested_owner_role="HR coordinator",
    )
    assert a.gap_id != b.gap_id
    assert a.thread_key == scope.thread_key
    path = gaps_jsonl_path(scope)
    assert path.is_file()
    recent = list_recent_gaps(scope, limit=10)
    assert len(recent) == 2
    assert recent[0].title == "Missing calibration log"
    assert recent[1].title == "Training matrix stale"


def test_list_recent_respects_limit(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    for i in range(5):
        append_gap_record(
            scope,
            title=f"Gap {i}",
            summary="s",
            severity="low",
            suggested_owner_role="Owner",
        )
    got = list_recent_gaps(scope, limit=2)
    assert len(got) == 2
    assert got[0].title == "Gap 3"
    assert got[1].title == "Gap 4"


def test_normalize_severity_med(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    r = append_gap_record(
        scope,
        title="t",
        summary="s",
        severity="med",
        suggested_owner_role="o",
    )
    assert r.severity == "medium"


def test_append_rejects_bad_severity(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    with pytest.raises(ValueError):
        append_gap_record(
            scope,
            title="t",
            summary="s",
            severity="critical",
            suggested_owner_role="o",
        )


def test_list_skips_corrupt_line(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    append_gap_record(
        scope,
        title="Good",
        summary="ok",
        severity="low",
        suggested_owner_role="r",
    )
    path = gaps_jsonl_path(scope)
    text = path.read_text(encoding="utf-8")
    path.write_text("not json at all\n" + text, encoding="utf-8")
    rows = list_recent_gaps(scope, limit=10)
    assert len(rows) == 1
    assert rows[0].title == "Good"


def test_gap_record_json_roundtrip() -> None:
    raw = (
        '{"gap_id":"g1","created_at":"2020-01-01T00:00:00+00:00",'
        '"title":"T","summary":"S","severity":"low",'
        '"suggested_owner_role":"R","iso_clause_refs":"","evidence_refs":"","thread_key":"k"}'
    )
    r = GapRecord.model_validate_json(raw)
    assert r.gap_id == "g1"
