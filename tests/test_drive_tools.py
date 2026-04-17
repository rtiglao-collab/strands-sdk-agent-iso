"""Tests for Google Drive read-only tools."""

from __future__ import annotations

import pytest

from iso_agent.config import get_settings
from iso_agent.l1_router.context import inbound_dm
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.tools import drive_tools


def _scope() -> UserScope:
    return UserScope.from_context(inbound_dm(user_id="u", space="dm", thread="t"))


def test_build_drive_tools_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Must not inherit ``ISO_AGENT_DRIVE_ENABLED`` from the developer shell."""
    monkeypatch.setenv("ISO_AGENT_DRIVE_ENABLED", "false")
    get_settings.cache_clear()
    assert drive_tools.build_drive_tools(_scope()) == []


def test_build_drive_tools_empty_without_allowlist(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ISO_AGENT_DRIVE_ENABLED", "true")
    key = tmp_path / "sa.json"
    key.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key))
    monkeypatch.setenv("ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS", "")
    get_settings.cache_clear()
    assert drive_tools.build_drive_tools(_scope()) == []


def test_drive_list_folder_mocked(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ISO_AGENT_DRIVE_ENABLED", "true")
    key = tmp_path / "sa.json"
    key.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key))
    monkeypatch.setenv("ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS", "folderABC")
    get_settings.cache_clear()

    class _ListReq:
        def execute(self) -> dict:
            return {
                "files": [
                    {
                        "id": "f1",
                        "name": "gap-analysis.md",
                        "mimeType": "text/plain",
                        "modifiedTime": "2020-01-01T00:00:00Z",
                    }
                ]
            }

    class _FakeFiles:
        def list(self, **_kwargs: object) -> _ListReq:
            return _ListReq()

    class _FakeSvc:
        def files(self) -> _FakeFiles:
            return _FakeFiles()

    monkeypatch.setattr(
        drive_tools.drive_client,
        "build_drive_v3_service",
        lambda _path: _FakeSvc(),
    )
    tools = drive_tools.build_drive_tools(_scope())
    assert len(tools) == 2
    out = str(tools[0]("folderABC"))
    assert "gap-analysis" in out
    assert "f1" in out


def test_drive_list_rejects_unknown_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ISO_AGENT_DRIVE_ENABLED", "true")
    key = tmp_path / "sa.json"
    key.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key))
    monkeypatch.setenv("ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS", "folderABC")
    get_settings.cache_clear()

    monkeypatch.setattr(
        drive_tools.drive_client,
        "build_drive_v3_service",
        lambda _path: object(),
    )
    tools = drive_tools.build_drive_tools(_scope())
    out = str(tools[0]("notInListFolder"))
    assert "not_allowlisted" in out
