"""In-memory Notion MCP client for ``notion_tools`` unit tests."""

from __future__ import annotations

import json
from typing import Any

from strands.tools.mcp.mcp_types import MCPToolResult

from iso_agent.l3_runtime.integrations import notion_client


class _NamedTool:
    def __init__(self, name: str) -> None:
        self.mcp_tool = self
        self.name = name


class FakeNotionMcpClient:
    """Minimal MCPClient surface used by :class:`NotionMcpRuntime`."""

    def __init__(
        self,
        *,
        search_hits: list[dict[str, Any]] | None = None,
        fetch_ok_ids: set[str] | None = None,
        fetch_text_by_id: dict[str, str] | None = None,
        create_response: dict[str, Any] | None = None,
    ) -> None:
        self.search_hits = search_hits if search_hits is not None else []
        self.fetch_ok_ids = fetch_ok_ids if fetch_ok_ids is not None else set()
        self.fetch_text_by_id = fetch_text_by_id if fetch_text_by_id is not None else {}
        self.create_response = create_response

    def list_tools_sync(self) -> list[_NamedTool]:
        return [
            _NamedTool("notion-search"),
            _NamedTool("notion-fetch"),
            _NamedTool("notion-create-pages"),
        ]

    def call_tool_sync(
        self,
        tool_use_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: Any = None,
        meta: dict[str, Any] | None = None,
    ) -> MCPToolResult:
        del read_timeout_seconds, meta
        arguments = arguments or {}
        if "search" in name.lower():
            blob = json.dumps({"results": self.search_hits})
            return MCPToolResult(
                status="success",
                toolUseId=tool_use_id,
                content=[{"text": blob}],
            )
        if "fetch" in name.lower():
            raw_id = str(arguments.get("id", ""))
            try:
                nid = notion_client.normalize_notion_page_id(raw_id)
            except ValueError:
                return MCPToolResult(
                    status="error",
                    toolUseId=tool_use_id,
                    content=[{"text": "invalid_id"}],
                )
            ok = nid in self.fetch_ok_ids
            if ok:
                text = self.fetch_text_by_id.get(nid, "fetched body\nsecond line")
                return MCPToolResult(
                    status="success",
                    toolUseId=tool_use_id,
                    content=[{"text": text}],
                )
            return MCPToolResult(
                status="error",
                toolUseId=tool_use_id,
                content=[{"text": "not_found"}],
            )
        if "create" in name.lower() and "page" in name.lower():
            if self.create_response is not None:
                cr = self.create_response
            else:
                cr = {
                    "results": [
                        {
                            "id": "22222222-2222-4222-8222-222222222222",
                            "url": "https://notion.so/x",
                        }
                    ]
                }
            out: MCPToolResult = {
                "status": "success",
                "toolUseId": tool_use_id,
                "content": [{"text": json.dumps(cr)}],
                "structuredContent": cr,
            }
            return out
        return MCPToolResult(
            status="error",
            toolUseId=tool_use_id,
            content=[{"text": f"unhandled tool {name!r}"}],
        )
