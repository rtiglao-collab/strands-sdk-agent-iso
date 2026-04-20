# Notion hosted MCP (runtime)

All coordinator **`notion_*`** QMS tools (discovery, index, allowlists, read, draft create) call **Notion’s hosted MCP** (`https://mcp.notion.com/mcp`, streamable HTTP) using **user OAuth + PKCE**. Tokens live per user under `memory/users/<user_key>/notion/mcp_oauth.json` — **never commit** that file.

The Neuuf coordinator also merges the server’s **raw `notion_mcp_*`** tool list when OAuth is configured, so the model can call Notion-hosted operations (for example **get teams**) that are not wrapped as **`notion_*`** yet.

There is **no parallel `NOTION_TOKEN` REST path** in the coordinator tools anymore; optional `iso-agent[notion]` / `notion_client` remain for **id/title helpers** and manual scripts that still use the integration API if you choose.

Official references:

- [Connecting to Notion MCP](https://developers.notion.com/guides/mcp/get-started-with-mcp) (Other tools / transports)
- [Integrating your own MCP client](https://developers.notion.com/guides/mcp/build-mcp-client) (discovery, dynamic registration, refresh)
- [Supported MCP tools](https://developers.notion.com/docs/mcp-supported-tools)

## Configuration

| Env | Meaning |
|-----|---------|
| `ISO_AGENT_NOTION_TRANSPORT` | `hybrid` or `mcp_primary` (default **`hybrid`**) starts MCP when `mcp_oauth.json` exists; **`rest_only`** disables all **`notion_*`** tools |
| `ISO_AGENT_NOTION_MCP_URL` | Defaults to `https://mcp.notion.com/mcp` |
| `ISO_AGENT_NOTION_MCP_REDIRECT_URI` | Defaults to `http://127.0.0.1:8765/callback` (must match the login listener) |

`hybrid` vs `mcp_primary` only affects transport registration policy in config; **`notion_*`** behavior is MCP-backed whenever OAuth is available.

## Login (first-time OAuth)

1. Set transport to **`hybrid`** (default) or **`mcp_primary`**.
2. Run **`iso-notion-mcp-login`** / **`iso-neuuf-coordinator --notion-mcp-login`**, or start **`iso-neuuf-coordinator`** and call **`notion_mcp_oauth_interactive_login`** (interactive REPL only).
3. Complete the browser consent flow; tokens are written to `memory/users/<user_key>/notion/mcp_oauth.json`. The REPL reloads the coordinator after in-process login so **`notion_*`** tools can start the MCP session.

## Token persistence (no repeated browser login)

After the first OAuth, the runtime loads `mcp_oauth.json` and refreshes the access token when it is near expiry, using the stored `refresh_token`. If the authorization server omits `expires_in`, the client writes a synthetic `expires_at` (about one hour ahead) so it does not call refresh on every startup. If a refresh request fails (for example a brief network error), the last `access_token` is still used so Notion tools stay available; individual MCP calls may fail until refresh succeeds. Run browser OAuth again only when Notion has revoked access, or you intentionally switch user/workspace.

## Implementation mapping (code)

| `notion_*` surface | Hosted MCP tool (resolved at runtime) |
|--------------------|--------------------------------------|
| `notion_discover_connected_pages`, `notion_refresh_page_index` | `notion-search` (best-effort parse of results → page index) |
| `notion_read_page`, allowlist verify, live metadata | `notion-fetch` |
| `notion_create_qms_draft*` | `notion-create-pages` |

Allowlists and `memory/.../discovered_page_index.json` remain **app-side** gates and snapshots.

Notion’s docs note limits such as **no file uploads on hosted MCP**; attachments may need another path.
