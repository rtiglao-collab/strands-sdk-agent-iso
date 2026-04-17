#!/usr/bin/env python3
"""Regenerate tracked infrastructure docs under docs/generated/.

Run after changing layout, console scripts, or optional dependency groups:

    python scripts/sync_repo_docs.py

CI / pre-commit uses:

    python scripts/sync_repo_docs.py --check

Do not edit the generated markdown by hand.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_OPTIONAL_DEP_KEY = re.compile(r"^[A-Za-z0-9_-]+\s*=\s*")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_table_section(text: str, header: str) -> dict[str, str]:
    """Parse ``[header]`` key = \"value\" lines until the next ``[section]``."""
    lines = text.splitlines()
    in_section = False
    out: dict[str, str] = {}
    for raw in lines:
        stripped = raw.strip()
        if stripped == f"[{header}]":
            in_section = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = False
            continue
        if not in_section or not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        out[key.strip()] = value.strip().strip('"')
    return out


def _parse_project_scripts(pyproject: str) -> dict[str, str]:
    return _parse_table_section(pyproject, "project.scripts")


def _parse_optional_dependency_groups(pyproject: str) -> list[str]:
    lines = pyproject.splitlines()
    in_section = False
    groups: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped == "[project.optional-dependencies]":
            in_section = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = False
            continue
        if not in_section or not stripped or stripped.startswith("#"):
            continue
        if not _OPTIONAL_DEP_KEY.match(stripped):
            continue
        key, _, _ = stripped.partition("=")
        name = key.strip()
        if name:
            groups.append(name)
    return sorted(groups)


def _ascii_tree(root: Path, *, prefix: str = "", max_depth: int = 6) -> list[str]:
    lines: list[str] = []
    if max_depth == 0:
        return lines
    skip_names = {"__pycache__", ".mypy_cache", ".ruff_cache", ".DS_Store"}
    entries = sorted(
        [p for p in root.iterdir() if p.name not in skip_names],
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    for index, path in enumerate(entries):
        connector = "└── " if index == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{path.name}")
        extension = "    " if index == len(entries) - 1 else "│   "
        if path.is_dir():
            lines.extend(_ascii_tree(path, prefix=prefix + extension, max_depth=max_depth - 1))
    return lines


def _git_ls_files(repo: Path) -> list[str] | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return sorted(line for line in proc.stdout.splitlines() if line)


def _manifest_paths(repo: Path, tracked: list[str] | None) -> list[str]:
    dir_prefixes = (
        "src/iso_agent/",
        "docs/",
        "knowledge/",
        "skills/",
        "memory/",
        "secrets/",
        "scripts/",
        "tests/",
        ".cursor/rules/",
        "references/",
    )
    single_files = (
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        ".pre-commit-config.yaml",
        ".gitleaksignore",
    )

    def keep_path(path: str) -> bool:
        if path in single_files:
            return True
        return any(path.startswith(prefix) for prefix in dir_prefixes)

    if tracked is None:
        paths: list[str] = []
        for name in single_files:
            candidate = repo / name
            if candidate.is_file():
                paths.append(name)
        for prefix in dir_prefixes:
            base = repo / prefix
            if base.is_file():
                paths.append(prefix)
            elif base.is_dir():
                paths.extend(
                    sorted(
                        str(x.relative_to(repo))
                        for x in base.rglob("*")
                        if x.is_file() and "__pycache__" not in x.parts
                    )
                )
        return sorted(set(paths))
    return sorted(p for p in tracked if keep_path(p))


def build_markdown(repo: Path) -> str:
    pyproject_path = repo / "pyproject.toml"
    pyproject = _read_text(pyproject_path)
    scripts = _parse_project_scripts(pyproject)
    optional_groups = _parse_optional_dependency_groups(pyproject)
    pkg_root = repo / "src" / "iso_agent"
    tree_lines = _ascii_tree(pkg_root) if pkg_root.is_dir() else ["(missing src/iso_agent)"]
    tracked = _git_ls_files(repo)
    manifest = _manifest_paths(repo, tracked)

    script_rows = "\n".join(
        f"| `{name}` | `{target}` |" for name, target in sorted(scripts.items())
    )
    opt_rows = ", ".join(f"`{g}`" for g in optional_groups) or "(none)"
    manifest_lines = "\n".join(f"- `{p}`" for p in manifest)

    return f"""<!-- AUTO-GENERATED by scripts/sync_repo_docs.py — do not edit by hand -->

# Infrastructure inventory

Deterministic snapshot (no wall-clock timestamp so `pre-commit` stays stable). Refresh with:

`python scripts/sync_repo_docs.py`

Then commit this file. Pre-commit runs `sync_repo_docs.py --check`.

## Console entry points (`pyproject.toml`)

| Script | Target |
|--------|--------|
{script_rows}

## Optional dependency groups

{opt_rows}

## Package tree (`src/iso_agent/`)

```text
iso_agent/
{chr(10).join(tree_lines)}
```

## Tracked paths manifest

Key application, docs, guardrails, and references (from `git ls-files` when available):

{manifest_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if docs/generated/INFRASTRUCTURE.md would change.",
    )
    args = parser.parse_args()

    repo = _repo_root()
    out_path = repo / "docs" / "generated" / "INFRASTRUCTURE.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_markdown(repo)

    if args.check:
        if not out_path.is_file():
            print(
                "error=missing_generated_file | run: python scripts/sync_repo_docs.py",
                file=sys.stderr,
            )
            return 1
        existing = _read_text(out_path)
        # Normalize line endings for comparison
        if existing.replace("\r\n", "\n") != content.replace("\r\n", "\n"):
            print(
                "error=drift_detected | docs/generated/INFRASTRUCTURE.md is stale | "
                "run: python scripts/sync_repo_docs.py",
                file=sys.stderr,
            )
            return 1
        return 0

    out_path.write_text(content, encoding="utf-8", newline="\n")
    rel = out_path.relative_to(repo)
    print(f"wrote=<{rel}> | repo docs synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
