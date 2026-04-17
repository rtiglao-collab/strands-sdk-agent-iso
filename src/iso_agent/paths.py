"""Repository layout helpers (runtime paths, not import paths)."""

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SRC_ROOT = _PACKAGE_ROOT.parent
REPO_ROOT = _SRC_ROOT.parent
