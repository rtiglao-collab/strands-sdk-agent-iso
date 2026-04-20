"""Programmatic calls into Notion hosted MCP (OAuth) for ``notion_*`` tools."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from strands.tools.mcp import MCPClient
from strands.tools.mcp.mcp_types import MCPToolResult

from iso_agent.l3_runtime.integrations import notion_client

logger = logging.getLogger(__name__)

_UUID_LINE = re.compile(
    r"id\s*=\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def _raw_tool_name(tool_obj: Any) -> str:
    raw = getattr(tool_obj, "mcp_tool", tool_obj)
    return str(getattr(raw, "name", "") or "")


def _norm_tool_key(name: str) -> str:
    return name.lower().replace("_", "-")


def _resolve_tool_name(client: MCPClient, *candidates: str) -> str | None:
    """Return server tool name matching one of ``candidates`` (exact, then normalized)."""
    tools = client.list_tools_sync()
    names = [_raw_tool_name(t) for t in tools]
    for want in candidates:
        for n in names:
            if n == want:
                return n
    for want in candidates:
        wn = _norm_tool_key(want)
        for n in names:
            if _norm_tool_key(n) == wn:
                return n
    return None


def _resolve_tool_by_substrings(client: MCPClient, parts: tuple[str, ...]) -> str | None:
    """First registered tool whose normalized name contains every substring."""
    tools = client.list_tools_sync()
    for t in tools:
        n = _norm_tool_key(_raw_tool_name(t))
        if all(p in n for p in parts):
            return _raw_tool_name(t)
    return None


class NotionMcpRuntime:
    """Resolve Notion MCP tool names once and invoke them with small typed helpers."""

    def __init__(self, client: MCPClient) -> None:
        self._client = client
        self._search: str | None = None
        self._fetch: str | None = None
        self._create_pages: str | None = None
        self._load_tool_names()

    def _load_tool_names(self) -> None:
        self._search = _resolve_tool_name(
            self._client, "notion-search", "notion_search", "search"
        ) or _resolve_tool_by_substrings(self._client, ("notion", "search"))
        self._fetch = _resolve_tool_name(
            self._client, "notion-fetch", "notion_fetch", "fetch"
        ) or _resolve_tool_by_substrings(self._client, ("notion", "fetch"))
        self._create_pages = _resolve_tool_name(
            self._client, "notion-create-pages", "notion_create_pages", "create-pages"
        ) or _resolve_tool_by_substrings(self._client, ("notion", "create", "page"))
        if not self._search:
            logger.warning("notion_mcp_runtime=missing_tool kind=search")
        if not self._fetch:
            logger.warning("notion_mcp_runtime=missing_tool kind=fetch")
        if not self._create_pages:
            logger.warning("notion_mcp_runtime=missing_tool kind=create_pages")

    def _call(self, name: str | None, arguments: dict[str, Any]) -> MCPToolResult:
        if not name:
            return MCPToolResult(
                status="error",
                toolUseId="iso-notion-mcp",
                content=[{"text": "error=no_mcp_tool | Notion MCP tool not found on server"}],
            )
        return self._client.call_tool_sync(str(uuid.uuid4()), name, arguments)

    @staticmethod
    def result_text(res: MCPToolResult) -> str:
        parts: list[str] = []
        for block in res.get("content", []) or []:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        sc = res.get("structuredContent")
        if isinstance(sc, (dict, list)):
            parts.append(json.dumps(sc, indent=2)[:120_000])
        return "\n".join(p for p in parts if p).strip()

    def search_pages(self, *, query: str, page_size: int) -> list[dict[str, Any]]:
        """Return page dicts for ``notion_page_index_store.merge_discovery_hits``."""
        if not self._search:
            return []
        args: dict[str, Any] = {"query": query.strip()}
        if page_size > 0:
            args["page_size"] = min(page_size, 100)
        res = self._call(self._search, args)
        blob = self.result_text(res)
        pages = _extract_page_objects(blob, res)
        out: list[dict[str, Any]] = []
        for p in pages:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id", "")).strip()
            if not pid:
                continue
            try:
                notion_client.normalize_notion_page_id(pid)
            except ValueError:
                continue
            out.append(p)
        if not out and blob:
            for m in _UUID_LINE.finditer(blob):
                try:
                    norm = notion_client.normalize_notion_page_id(m.group(1))
                except ValueError:
                    continue
                synthetic: dict[str, Any] = {
                    "object": "page",
                    "id": norm,
                    "url": "",
                    "properties": {},
                    "parent": {},
                }
                out.append(synthetic)
        return out[:page_size]

    def fetch_page_text(self, *, page_id: str) -> str:
        if not self._fetch:
            return ""
        pid = notion_client.normalize_notion_page_id(page_id)
        res = self._call(self._fetch, {"id": pid})
        if res.get("status") != "success":
            return ""
        return self.result_text(res).strip()

    def page_accessible(self, *, page_id: str) -> tuple[bool, str]:
        if not self._fetch:
            return False, "no_fetch_tool"
        pid = notion_client.normalize_notion_page_id(page_id)
        res = self._call(self._fetch, {"id": pid})
        if res.get("status") != "success":
            return False, self.result_text(res)[:500] or "fetch_failed"
        text = self.result_text(res)
        if not text.strip():
            return False, "empty_fetch"
        return True, ""

    def fetch_page_summary_live(self, *, page_id: str) -> dict[str, Any] | None:
        """Small summary dict for ``notion_page_metadata`` live branch (best-effort)."""
        if not self._fetch:
            return None
        pid = notion_client.normalize_notion_page_id(page_id)
        res = self._call(self._fetch, {"id": pid})
        if res.get("status") != "success":
            return None
        text = self.result_text(res)
        sc = res.get("structuredContent")
        if isinstance(sc, dict) and sc.get("id"):
            raw = sc
        else:
            raw = _try_json_dict(text) or {}
        pid_out = str(raw.get("id", pid))
        try:
            pid_out = notion_client.normalize_notion_page_id(pid_out)
        except ValueError:
            pid_out = pid
        return {
            "id": pid_out,
            "url": str(raw.get("url", "")),
            "parent": raw.get("parent") if isinstance(raw.get("parent"), dict) else {},
            "created_time": raw.get("created_time", ""),
            "last_edited_time": raw.get("last_edited_time", ""),
            "archived": raw.get("archived", False),
            "in_trash": raw.get("in_trash", False),
            "title_plain": notion_client.page_plain_title(raw) if raw else "",
            "property_schema_keys": sorted((raw.get("properties") or {}).keys())
            if isinstance(raw.get("properties"), dict)
            else [],
        }

    def create_child_page(
        self, *, parent_page_id: str, title: str, body: str
    ) -> dict[str, Any]:
        if not self._create_pages:
            return {"id": "", "url": "", "error": "no_create_pages_tool"}
        parent = notion_client.normalize_notion_page_id(parent_page_id)
        pages_payload: list[dict[str, Any]] = [
            {
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title[:2000]}}],
                    },
                },
                "content": body.strip() or " ",
            }
        ]
        res = self._call(
            self._create_pages,
            {"parent": {"page_id": parent}, "pages": pages_payload},
        )
        text = self.result_text(res)
        if res.get("status") != "success":
            return {"id": "", "url": "", "error": text[:2000]}
        sc = res.get("structuredContent")
        if isinstance(sc, dict):
            results = sc.get("results") or sc.get("pages") or sc.get("created_pages")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    return {
                        "id": str(first.get("id", "")),
                        "url": str(first.get("url", "")),
                    }
        parsed = _try_json_dict(text) or _try_json_dict(text.split("\n", 1)[0])
        if isinstance(parsed, dict):
            pid = str(parsed.get("id", parsed.get("page_id", "")))
            if pid:
                try:
                    pid = notion_client.normalize_notion_page_id(pid)
                except ValueError:
                    pass
                return {"id": pid, "url": str(parsed.get("url", ""))}
        return {"id": "", "url": "", "error": text[:2000] or "create_parse_failed"}


def _try_json_dict(text: str) -> dict[str, Any] | None:
    t = text.strip()
    if not t:
        return None
    try:
        val: Any = json.loads(t)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, dict) else None


def _extract_page_objects(blob: str, res: MCPToolResult) -> list[dict[str, Any]]:
    sc = res.get("structuredContent")
    acc: list[dict[str, Any]] = []
    if isinstance(sc, dict):
        _collect_page_like(sc, acc)
    if isinstance(sc, list):
        _collect_page_like(sc, acc)
    if not acc:
        parsed = _try_json_dict(blob)
        if parsed is not None:
            _collect_page_like(parsed, acc)
    if not acc:
        for line in blob.splitlines():
            parsed = _try_json_dict(line)
            if parsed is not None:
                _collect_page_like(parsed, acc)
    return acc


def _collect_page_like(obj: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        if obj.get("object") == "page" and obj.get("id"):
            out.append(obj)
            return
        for v in obj.values():
            _collect_page_like(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_page_like(v, out)
