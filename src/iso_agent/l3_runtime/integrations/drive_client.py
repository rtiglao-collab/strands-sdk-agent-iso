"""Google Drive API v3 read-only helpers (service account).

Uses ``GOOGLE_APPLICATION_CREDENTIALS`` (path to JSON) from the environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol, cast

logger = logging.getLogger(__name__)

_DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"


class _DriveService(Protocol):
    def files(self) -> Any: ...


def build_drive_v3_service(credentials_path: str) -> _DriveService:
    """Build a Drive v3 API service with read-only scope."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    path = Path(credentials_path)
    if not path.is_file():
        msg = f"credentials_path=<{credentials_path}> | not a file"
        raise FileNotFoundError(msg)
    creds = service_account.Credentials.from_service_account_file(
        str(path),
        scopes=[_DRIVE_READONLY],
    )
    return cast(
        _DriveService,
        build("drive", "v3", credentials=creds, cache_discovery=False),
    )


def list_children(
    service: _DriveService,
    folder_id: str,
    *,
    page_size: int,
) -> list[dict[str, str]]:
    """List non-trashed files directly under ``folder_id``."""
    resp = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=page_size,
            fields="files(id,name,mimeType,modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    raw = resp.get("files", [])
    out: list[dict[str, str]] = []
    for item in raw:
        out.append(
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "mimeType": str(item.get("mimeType", "")),
                "modifiedTime": str(item.get("modifiedTime", "")),
            }
        )
    return out


def get_file_metadata(service: _DriveService, file_id: str) -> dict[str, Any]:
    """Return id, name, mimeType, parents for a file."""
    raw = (
        service.files()
        .get(
            fileId=file_id,
            fields="id,name,mimeType,parents",
            supportsAllDrives=True,
        )
        .execute()
    )
    return cast(dict[str, Any], raw)


def export_file_text(service: _DriveService, file_id: str, mime_type: str) -> str:
    """Export Google Workspace files to text; ``mime_type`` is the Drive file mimeType."""
    if mime_type == "application/vnd.google-apps.document":
        export_mime = "text/plain"
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        export_mime = "text/csv"
    elif mime_type == "application/vnd.google-apps.presentation":
        return (
            "mime_type=presentation | export not supported in Phase 3; open in Drive UI"
        )
    else:
        return (
            f"mime_type=<{mime_type}> | export not supported in Phase 3; "
            "open in Drive UI or add a parser"
        )
    raw_bytes = (
        service.files()
        .export_media(fileId=file_id, mimeType=export_mime)
        .execute()
    )
    data = cast(bytes, raw_bytes)
    text = data.decode("utf-8", errors="replace")
    return text


def parents_allowlisted(meta: dict[str, Any], allowed_folder_ids: set[str]) -> bool:
    """Return True if any parent folder id is in the allowlist."""
    parents = meta.get("parents") or []
    if not isinstance(parents, list):
        return False
    return any(p in allowed_folder_ids for p in parents)


def file_id_allowlisted(file_id: str, allowed_file_ids: set[str]) -> bool:
    return file_id in allowed_file_ids
