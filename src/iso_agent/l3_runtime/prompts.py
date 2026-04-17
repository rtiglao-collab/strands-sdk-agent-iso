"""Load markdown role prompts from ``knowledge/agents/``."""

from iso_agent.paths import REPO_ROOT


def load_role_prompt(role_slug: str) -> str:
    """Return trimmed markdown for ``knowledge/agents/<role_slug>.md``.

    Args:
        role_slug: File stem under ``knowledge/agents/`` (for example ``researcher``).

    Returns:
        File contents.

    Raises:
        FileNotFoundError: If the prompt file is missing.
    """
    path = REPO_ROOT / "knowledge" / "agents" / f"{role_slug}.md"
    if not path.is_file():
        msg = f"prompt_file=<{path}> | missing role prompt"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8").strip()
