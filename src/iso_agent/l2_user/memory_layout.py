"""Filesystem layout for per-user state under `memory/users/`."""

from hashlib import sha256
from pathlib import Path

from iso_agent.paths import REPO_ROOT


def stable_user_key(platform_user_id: str) -> str:
    """Derive an opaque, stable key from the platform user id."""
    digest = sha256(platform_user_id.encode("utf-8")).hexdigest()
    return digest[:24]


def user_memory_dir(user_key: str) -> Path:
    """Return the absolute directory for a user's memory partition."""
    return REPO_ROOT / "memory" / "users" / user_key


def ensure_user_memory_dir(user_key: str) -> Path:
    """Ensure `memory/users/<user_key>/` exists and return it."""
    path = user_memory_dir(user_key)
    path.mkdir(parents=True, exist_ok=True)
    return path
