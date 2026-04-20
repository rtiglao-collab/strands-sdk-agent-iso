#!/usr/bin/env python3
"""Live integration smoke: Perplexity, Drive (gap-named file), Notion discovery.

Run from the repo root with secrets in the environment or a local ``.env`` file::

    cd /path/to/strands-sdk-agent-iso && source .venv/bin/activate
    python scripts/run_integration_smoke.py

Does not print secret values. Exits ``0`` if all attempted checks pass, ``1`` otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_IN_REPO_GAP_ANALYST = _REPO / "knowledge" / "agents" / "gap_analyst.md"


def _perplexity_line() -> tuple[str, bool]:
    from iso_agent.config import get_settings
    from iso_agent.l3_runtime.integrations import perplexity

    get_settings.cache_clear()
    ok = perplexity.perplexity_mcp_configured()
    transport = get_settings().perplexity_transport
    has_key = bool(__import__("os").environ.get("PERPLEXITY_API_KEY", "").strip())
    msg = (
        f"perplexity transport=<{transport}> key_set=<{has_key}> "
        f"mcp_ready=<{ok}> | researcher can attach Perplexity MCP when all true"
    )
    return msg, ok or transport == "disabled"


def _drive_gap_doc() -> tuple[str, bool]:
    import os

    from iso_agent.config import get_settings
    from iso_agent.l3_runtime.integrations import drive_client

    get_settings.cache_clear()
    s = get_settings()
    if not s.drive_enabled:
        return "drive skipped | ISO_AGENT_DRIVE_ENABLED is false", True
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not cred:
        return "drive fail | GOOGLE_APPLICATION_CREDENTIALS unset", False
    raw_folders = s.drive_allowed_folder_ids.replace("\n", ",").split(",")
    folders = [p.strip() for p in raw_folders if p.strip()]
    if not folders:
        return "drive fail | ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS empty", False
    folder_id = folders[0]
    try:
        service = drive_client.build_drive_v3_service(cred)
        rows = drive_client.list_children(service, folder_id, page_size=min(s.drive_max_list, 50))
        gap_rows = [r for r in rows if "gap" in r["name"].lower()]
        if not gap_rows:
            names = ", ".join(r["name"] for r in rows[:8])
            return (
                f"drive listed folder=<{folder_id}> files={len(rows)} | "
                f"no filename containing 'gap' (first names: {names or '(none)'})",
                True,
            )
        target = gap_rows[0]
        fid, name, mime = target["id"], target["name"], target["mimeType"]
        meta = drive_client.get_file_metadata(service, fid)
        raw_files = s.drive_allowed_file_ids.replace("\n", ",").split(",")
        allowed_f = {p.strip() for p in raw_files if p.strip()}
        parents_ok = drive_client.parents_allowlisted(meta, set(folders))
        files_ok = drive_client.file_id_allowlisted(fid, allowed_f)
        if not (parents_ok or files_ok):
            return f"drive fail | file=<{name}> not allowlisted by parent or file id list", False
        body = drive_client.export_file_text(service, fid, mime)
        preview = (body[:800] + "…") if len(body) > 800 else body
        preview_one_line = preview.replace("\n", " ")[:400]
        return (
            f"drive read gap-related file name=<{name!r}> id=<{fid}> mime=<{mime}> "
            f"preview=<{preview_one_line}>",
            True,
        )
    except Exception as exc:
        detail = str(exc).replace("\n", " ")[:320]
        hint = ""
        low = detail.lower()
        if "accessnotconfigured" in low or "has not been used" in low or "403" in detail:
            hint = (
                " | fix: Google Cloud Console APIs and Services enable Drive API for the "
                "project that owns this service account, then retry after a few minutes"
            )
        return f"drive fail | exc_type={type(exc).__name__} detail=<{detail}>{hint}", False


def _notion_discovery() -> tuple[str, bool]:
    from iso_agent.config import get_settings
    from iso_agent.l1_router.context import inbound_dm
    from iso_agent.l2_user.user_scope import UserScope
    from iso_agent.l3_runtime.integrations import notion_client, notion_mcp
    from iso_agent.l3_runtime.integrations.notion_mcp_runtime import NotionMcpRuntime

    get_settings.cache_clear()
    s = get_settings()
    if not s.notion_enabled:
        return "notion skipped | ISO_AGENT_NOTION_ENABLED=false (opt-out)", True
    if s.notion_transport == "rest_only":
        return "notion skipped | ISO_AGENT_NOTION_TRANSPORT=rest_only", True
    if not s.notion_discovery_enabled:
        return (
            "notion discovery skipped | ISO_AGENT_NOTION_DISCOVERY_ENABLED=false (opt-out); "
            "defaults on when unset",
            True,
        )
    scope = UserScope.from_context(inbound_dm(user_id="smoke", space="dm", thread="smoke"))
    mcp = notion_mcp.ensure_notion_mcp_client(scope)
    if mcp is None:
        return (
            "notion skipped | no Notion MCP OAuth for smoke scope "
            "(memory/users/.../notion/mcp_oauth.json — run iso-notion-mcp-login)",
            True,
        )
    try:
        hits = NotionMcpRuntime(mcp).search_pages(query="", page_size=15)
    except Exception as exc:
        return f"notion discover fail | exc_type={type(exc).__name__}", False
    lines: list[str] = []
    for page in hits[:15]:
        pid = str(page.get("id", ""))
        title = notion_client.page_plain_title(page)
        parent = page.get("parent", {})
        lines.append(f"  - {pid} | {title!r} | parent={parent}")
    block = "\n".join(lines) if lines else "  (no pages returned)"
    return f"notion discover via MCP (n={len(hits)}):\n{block}", True


def _in_repo_gap_prompt() -> str:
    if _IN_REPO_GAP_ANALYST.is_file():
        text = _IN_REPO_GAP_ANALYST.read_text(encoding="utf-8")
        snip = text[:600].replace("\n", " ")
        return (
            f"in-repo gap analyst prompt: path=<{_IN_REPO_GAP_ANALYST.relative_to(_REPO)}> "
            f"chars={len(text)} start=<{snip}…>"
        )
    return f"in-repo gap analyst prompt: missing file <{_IN_REPO_GAP_ANALYST}>"


def main() -> int:
    from iso_agent.config import get_settings

    get_settings.cache_clear()

    ok_all = True
    for label, fn in (
        ("1_repo_gap_prompt", lambda: (_in_repo_gap_prompt(), True)),
        ("2_perplexity", _perplexity_line),
        ("3_drive_gap_file", _drive_gap_doc),
        ("4_notion_discover", _notion_discovery),
    ):
        msg, ok = fn()
        print(f"[{label}] {msg}")
        if not ok:
            ok_all = False
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
