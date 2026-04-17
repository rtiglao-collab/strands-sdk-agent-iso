"""Per-user Notion allowlists persisted under ``memory/users/<user_key>/notion/``.

Supplements ``ISO_AGENT_NOTION_ALLOWED_PAGE_IDS`` and ``ISO_AGENT_NOTION_ALLOWED_PARENT_IDS``.
The coordinator can add or remove UUIDs at runtime via tools; merged allowlists are
``environment ∪ disk`` on every read/create call.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from iso_agent.config import Settings
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import notion_client

logger = logging.getLogger(__name__)

_MAX_IDS_PER_CHANNEL = 200
_FILE_NAME = "allowlist.json"


class PersistedNotionAllowlist(BaseModel):
    """On-disk shape for Notion read/draft allowlists."""

    version: int = 1
    page_ids: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)


def notion_allowlist_dir(scope: UserScope) -> Path:
    """Return ``memory_root/notion``, creating it if needed."""
    d = scope.memory_root / "notion"
    d.mkdir(parents=True, exist_ok=True)
    return d


def notion_allowlist_path(scope: UserScope) -> Path:
    """Path to persisted allowlist JSON for this user."""
    return notion_allowlist_dir(scope) / _FILE_NAME


def _normalize_list(raw: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    skipped = 0
    seen: set[str] = set()
    for item in raw:
        try:
            n = notion_client.normalize_notion_page_id(str(item))
        except ValueError:
            skipped += 1
            continue
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out[:_MAX_IDS_PER_CHANNEL], skipped


def load_persisted_allowlist(scope: UserScope) -> tuple[set[str], set[str]]:
    """Return page and parent id sets from disk (may be empty)."""
    path = notion_allowlist_path(scope)
    if not path.is_file():
        return set(), set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        data = PersistedNotionAllowlist.model_validate(raw)
    except Exception as exc:
        logger.warning(
            "notion_allowlist=load_failed path=<%s> exc_type=<%s>",
            path,
            type(exc).__name__,
            exc_info=exc,
        )
        return set(), set()
    pages, _ = _normalize_list(list(data.page_ids))
    parents, _ = _normalize_list(list(data.parent_ids))
    return set(pages), set(parents)


def save_persisted_allowlist(scope: UserScope, pages: set[str], parents: set[str]) -> None:
    """Write allowlists to disk (deduped, capped)."""
    path = notion_allowlist_path(scope)
    p_list, _ = _normalize_list(sorted(pages))
    par_list, _ = _normalize_list(sorted(parents))
    data = PersistedNotionAllowlist(page_ids=p_list, parent_ids=par_list)
    path.write_text(data.model_dump_json(indent=2) + "\n", encoding="utf-8")


def parse_uuid_csv(raw: str) -> set[str]:
    """Parse comma- or newline-separated Notion UUIDs into a normalized set."""
    out: set[str] = set()
    for part in raw.replace("\n", ",").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.add(notion_client.normalize_notion_page_id(p))
        except ValueError:
            logger.debug("notion_allowlist=skip_invalid_uuid raw_prefix=<%s>", p[:16])
    return out


def merged_page_ids(scope: UserScope, settings: Settings) -> set[str]:
    """Environment ∪ persisted read page ids."""
    return parse_uuid_csv(settings.notion_allowed_page_ids) | load_persisted_allowlist(scope)[0]


def merged_parent_ids(scope: UserScope, settings: Settings) -> set[str]:
    """Environment ∪ persisted draft parent ids."""
    return parse_uuid_csv(settings.notion_allowed_parent_ids) | load_persisted_allowlist(scope)[1]


def add_persisted_read_page(scope: UserScope, page_id: str) -> tuple[bool, str]:
    """Append a read page id to disk allowlist. Caller must verify Notion access."""
    norm = notion_client.normalize_notion_page_id(page_id)
    pages, parents = load_persisted_allowlist(scope)
    if norm in pages:
        return True, "already_present"
    if len(pages) >= _MAX_IDS_PER_CHANNEL:
        return False, "persisted_page_allowlist_full"
    pages.add(norm)
    save_persisted_allowlist(scope, pages, parents)
    return True, "ok"


def add_persisted_draft_parent(scope: UserScope, parent_page_id: str) -> tuple[bool, str]:
    """Append a draft parent id to disk allowlist."""
    norm = notion_client.normalize_notion_page_id(parent_page_id)
    pages, parents = load_persisted_allowlist(scope)
    if norm in parents:
        return True, "already_present"
    if len(parents) >= _MAX_IDS_PER_CHANNEL:
        return False, "persisted_parent_allowlist_full"
    parents.add(norm)
    save_persisted_allowlist(scope, pages, parents)
    return True, "ok"


def remove_persisted_read_page(scope: UserScope, page_id: str) -> tuple[bool, str]:
    """Remove a read page id from disk only (cannot remove env-only ids)."""
    norm = notion_client.normalize_notion_page_id(page_id)
    pages, parents = load_persisted_allowlist(scope)
    if norm not in pages:
        return False, "not_in_persisted_allowlist"
    pages.discard(norm)
    save_persisted_allowlist(scope, pages, parents)
    return True, "ok"


def remove_persisted_draft_parent(scope: UserScope, parent_page_id: str) -> tuple[bool, str]:
    """Remove a draft parent id from disk only."""
    norm = notion_client.normalize_notion_page_id(parent_page_id)
    pages, parents = load_persisted_allowlist(scope)
    if norm not in parents:
        return False, "not_in_persisted_allowlist"
    parents.discard(norm)
    save_persisted_allowlist(scope, pages, parents)
    return True, "ok"


def format_allowlist_status(scope: UserScope, settings: Settings) -> str:
    """Human-readable summary for notion_allowlist_list (no secrets)."""
    file_pages, file_parents = load_persisted_allowlist(scope)
    env_pages = parse_uuid_csv(settings.notion_allowed_page_ids)
    env_parents = parse_uuid_csv(settings.notion_allowed_parent_ids)
    merged_p = env_pages | file_pages
    merged_par = env_parents | file_parents
    path = notion_allowlist_path(scope)
    rel = path.relative_to(scope.memory_root)
    return (
        f"path=<{rel}> | "
        f"env_read_count=<{len(env_pages)}> env_draft_parent_count=<{len(env_parents)}> | "
        f"file_read_count=<{len(file_pages)}> file_draft_parent_count=<{len(file_parents)}> | "
        f"merged_read_count=<{len(merged_p)}> merged_draft_parent_count=<{len(merged_par)}> | "
        f"file_read_preview=<{','.join(sorted(file_pages)[:8])}> | "
        f"file_draft_preview=<{','.join(sorted(file_parents)[:8])}>"
    )
