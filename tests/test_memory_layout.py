"""Tests for L2 path helpers."""

from iso_agent.l2_user.memory_layout import stable_user_key, user_memory_dir
from iso_agent.paths import REPO_ROOT


def test_stable_user_key_is_deterministic() -> None:
    assert stable_user_key("alice") == stable_user_key("alice")
    assert stable_user_key("alice") != stable_user_key("bob")


def test_user_memory_dir_under_repo() -> None:
    key = stable_user_key("alice")
    path = user_memory_dir(key)
    assert path.is_absolute()
    assert path.parts[-3:] == ("memory", "users", key)
    assert REPO_ROOT in path.parents
