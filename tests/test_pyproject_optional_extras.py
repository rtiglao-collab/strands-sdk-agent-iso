"""Sanity checks for declared optional dependency groups."""

from __future__ import annotations

from pathlib import Path

import tomllib


def _pyproject() -> dict:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def test_excel_extra_includes_openpyxl() -> None:
    data = _pyproject()
    excel = data["project"]["optional-dependencies"]["excel"]
    assert any("openpyxl" in str(line) for line in excel)


def test_requirements_excel_txt_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    body = (root / "requirements-excel.txt").read_text(encoding="utf-8")
    assert "openpyxl" in body
