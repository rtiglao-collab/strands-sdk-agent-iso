"""Tests for scripts/sync_repo_docs.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_sync_module():
    path = ROOT / "scripts" / "sync_repo_docs.py"
    spec = importlib.util.spec_from_file_location("_sync_repo_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_project_scripts() -> None:
    mod = _load_sync_module()
    text = '[project.scripts]\niso-x = "pkg:mod:fn"\n\n[tool.other]\nx=1\n'
    assert mod._parse_project_scripts(text) == {"iso-x": "pkg:mod:fn"}


def test_parse_optional_dependency_groups() -> None:
    mod = _load_sync_module()
    text = (
        "[project.optional-dependencies]\n"
        "openai = []\n"
        "dev = [\n"
        '  "pytest",\n'
        "]\n"
        "[tool.ruff]\n"
    )
    assert mod._parse_optional_dependency_groups(text) == ["dev", "openai"]


def test_build_markdown_is_deterministic(tmp_path: Path) -> None:
    mod = _load_sync_module()
    (tmp_path / "pyproject.toml").write_text(
        "[project.scripts]\n"
        'iso-x = "pkg:mod:fn"\n'
        "[project.optional-dependencies]\n"
        "openai = []\n",
        encoding="utf-8",
    )
    pkg = tmp_path / "src" / "iso_agent"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")

    first = mod.build_markdown(tmp_path)
    second = mod.build_markdown(tmp_path)
    assert first == second
    assert "iso-x" in first
    assert "pkg:mod:fn" in first
