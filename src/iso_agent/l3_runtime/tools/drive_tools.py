"""Google Drive read-only tools for the Neuuf coordinator (Phase 3)."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from strands.tools.decorator import tool

from iso_agent.config import get_settings
from iso_agent.l2_user.user_scope import UserScope
from iso_agent.l3_runtime.integrations import drive_client

logger = logging.getLogger(__name__)

_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,128}$")


def _validate_drive_id(value: str, label: str) -> str | None:
    if not _DRIVE_ID_RE.match(value):
        return f"error=invalid_{label}_format"
    return None


def _parse_id_set(raw: str) -> set[str]:
    return {part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()}


def build_drive_tools(scope: UserScope) -> list[Any]:
    """Build Drive tools when enabled, credentialed, and allowlists are non-empty."""
    settings = get_settings()
    if not settings.drive_enabled:
        return []

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not cred_path:
        logger.warning("drive=creds_env_missing | GOOGLE_APPLICATION_CREDENTIALS unset")
        return []

    allowed_folders = _parse_id_set(settings.drive_allowed_folder_ids)
    allowed_files = _parse_id_set(settings.drive_allowed_file_ids)
    if not allowed_folders and not allowed_files:
        logger.warning("drive=allowlist_empty | set ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS")
        return []

    try:
        service = drive_client.build_drive_v3_service(cred_path)
    except ImportError as exc:
        logger.warning(
            "drive=import_failed hint=<%s> exc_type=<%s>",
            "pip install iso-agent[drive]",
            type(exc).__name__,
            exc_info=exc,
        )
        return []
    except Exception as exc:
        logger.warning("drive=service_build_failed exc_type=<%s>", type(exc).__name__, exc_info=exc)
        return []

    max_list = max(1, min(settings.drive_max_list, 100))

    @tool(
        name="drive_list_folder",
        description=(
            "List files in a Google Drive folder (read-only). folder_id must be in the "
            "deployment allowlist."
        ),
    )
    def drive_list_folder(folder_id: str) -> str:
        """List up to ``drive_max_list`` files in an allowed folder."""
        logger.debug("drive_list_folder user_key=<%s> folder_id=<%s>", scope.user_key, folder_id)
        bad = _validate_drive_id(folder_id, "folder_id")
        if bad:
            return bad
        if folder_id not in allowed_folders:
            return "error=folder_not_allowlisted | request an allowed folder_id from ops"
        try:
            rows = drive_client.list_children(service, folder_id, page_size=max_list)
        except Exception as exc:
            logger.warning(
                "drive=list_failed folder_id=<%s> exc_type=<%s>",
                folder_id,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=list_failed | check service account access to this folder"
        if not rows:
            return f"empty_folder=<{folder_id}>"
        lines = ["id | name | mimeType | modifiedTime", "---|---|---|---"]
        for r in rows:
            mt = r["mimeType"]
            mod = r.get("modifiedTime", "")
            lines.append(f"{r['id']} | {r['name']} | {mt} | {mod}")
        return "\n".join(lines)

    @tool(
        name="drive_read_document",
        description=(
            "Export a Google Doc or Sheet as text when its parent folder is allowlisted "
            "or its file id is explicitly allowlisted."
        ),
    )
    def drive_read_document(file_id: str, max_chars: int = 12000) -> str:
        """Read document text from Drive (truncated)."""
        logger.debug("drive_read_document user_key=<%s> file_id=<%s>", scope.user_key, file_id)
        bad = _validate_drive_id(file_id, "file_id")
        if bad:
            return bad
        max_chars = max(1000, min(max_chars, 200000))
        try:
            meta = drive_client.get_file_metadata(service, file_id)
        except Exception as exc:
            logger.warning(
                "drive=meta_failed file_id=<%s> exc_type=<%s>",
                file_id,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=metadata_failed | verify file id and permissions"
        fid = str(meta.get("id", ""))
        mime_type = str(meta.get("mimeType", ""))
        if mime_type == "application/vnd.google-apps.folder":
            return "error=is_folder | use drive_list_folder"
        parents_ok = drive_client.parents_allowlisted(meta, allowed_folders)
        files_ok = drive_client.file_id_allowlisted(fid, allowed_files)
        ok = parents_ok or files_ok
        if not ok:
            return "error=file_not_allowlisted | parent must be under allowed folders"
        try:
            body = drive_client.export_file_text(service, fid, mime_type)
        except Exception as exc:
            logger.warning(
                "drive=export_failed file_id=<%s> exc_type=<%s>",
                fid,
                type(exc).__name__,
                exc_info=exc,
            )
            return "error=export_failed"
        if len(body) > max_chars:
            return body[:max_chars] + "\n...truncated..."
        return body

    return [drive_list_folder, drive_read_document]
