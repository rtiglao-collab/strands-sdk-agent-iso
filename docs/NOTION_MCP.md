# Notion hosted MCP (runtime)

This repo can attach **Notion’s hosted MCP** (`https://mcp.notion.com/mcp`, streamable HTTP) to the Neuuf coordinator **in addition to** the existing **REST** tools driven by `NOTION_TOKEN` (internal integration). They use **different auth**: MCP is **user OAuth + PKCE** with tokens stored per user under `memory/users/<user_key>/notion/mcp_oauth.json` — **never commit** that file.

Official references:

- [Connecting to Notion MCP](https://developers.notion.com/guides/mcp/get-started-with-mcp) (Other tools / transports)
- [Integrating your own MCP client](https://developers.notion.com/guides/mcp/build-mcp-client) (discovery, dynamic registration, refresh)

## Configuration

| Env | Meaning |
|-----|---------|
| `ISO_AGENT_NOTION_TRANSPORT` | `rest_only` (default), `hybrid`, or `mcp_primary` |
| `ISO_AGENT_NOTION_MCP_URL` | Defaults to `https://mcp.notion.com/mcp` |
| `ISO_AGENT_NOTION_MCP_REDIRECT_URI` | Defaults to `http://127.0.0.1:8765/callback` (must match the login listener) |

`NOTION_TOKEN` and REST `notion_*` tools are unchanged unless you choose `mcp_primary` (see below).

## Login (first-time OAuth)

1. Set `ISO_AGENT_NOTION_TRANSPORT=hybrid` or `mcp_primary`.
2. Run **`iso-notion-mcp-login`** (same memory scope as `iso-neuuf-coordinator` when you pass `--user-id local-dev`), or **`iso-neuuf-coordinator --notion-mcp-login`**.
3. Complete the browser consent flow; tokens are written to `memory/users/<user_key>/notion/mcp_oauth.json`.

## REST vs MCP parity (manual checklist)

After a successful login, run `list_tools` (or inspect coordinator startup logs for `notion_mcp=ready tool_count=…`) and fill in this table for **your** workspace. Tool names vary by Notion MCP version.

| REST / app capability | MCP tool(s) | Notes |
|----------------------|-------------|--------|
| `notion_discover_connected_pages` / search | _TBD_ | |
| `notion_read_page` (allowlisted) | _TBD_ | REST allowlists remain app-side |
| `notion_create_qms_draft*` | _TBD_ | |
| Workspace / team navigation | _TBD_ | Typical MCP strength vs REST search |

Notion’s FAQ notes limits such as **no file uploads on hosted MCP**; use REST or the file API for attachments if needed.

## `mcp_primary` mode

When `ISO_AGENT_NOTION_TRANSPORT=mcp_primary` **and** `mcp_oauth.json` exists, the REST tool **`notion_discover_connected_pages`** is **not** registered (MCP is expected to cover discovery). Allowlists, index files, and draft/read tools stay on the REST path until you map and migrate them explicitly.
