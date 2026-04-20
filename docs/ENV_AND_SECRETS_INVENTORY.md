# Environment variables and secret files (inventory)

Use this list when moving from **local exports** and **`secrets/`** files to **cloud** secret managers, CI variables, or mounted files. Names match what the code reads today (`src/iso_agent/config.py`, tools, adapters).

**Convention:** `ISO_AGENT_*` variables are loaded by `Settings` (see `config.py`). A few vendors use **standard names** without that prefix (`GOOGLE_APPLICATION_CREDENTIALS` for **`drive_tools`** unit tests only, `NOTION_TOKEN` for manual REST only, `PERPLEXITY_API_KEY`).

## Secret values (treat as credentials in prod)

| Name | Type | Used by | Local pattern | Cloud migration |
|------|------|---------|---------------|-----------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Filesystem path to JSON | **`drive_client` / `drive_tools` unit tests only** — not used by the Neuuf coordinator | `secrets/google/*.json` (gitignored) | Omit unless you run Drive-related tests locally |
| `NOTION_TOKEN` | String | Ad-hoc REST only (`tests/manual_notion_page_inspect.py`); **not** coordinator `notion_*` | export / secret manager | Optional; omit if you use MCP only |
| `PERPLEXITY_API_KEY` | String | Perplexity MCP (`perplexity.py`) | export | Secret manager |
| `ISO_AGENT_CHAT_WEBHOOK_SECRET` | String | Google Chat webhook (`google_chat_app.py`) | export | Secret manager; rotate with Chat app config |

## AWS (Bedrock default LLM)

| Name | Type | Notes |
|------|------|--------|
| Default credential chain | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, profiles, instance role | `boto3` / `BedrockModel` |
| `AWS_REGION` | String | Used if `ISO_AGENT_BEDROCK_REGION_NAME` unset |

## `ISO_AGENT_*` configuration (often non-secret)

| Variable | Purpose |
|----------|---------|
| `ISO_AGENT_PRIMARY_MODE` | `demo` \| `neuuf` — demo calculator vs Neuuf stack in `handle_user_message` |
| `ISO_AGENT_BEDROCK_MODEL_ID` | Bedrock model or inference profile id |
| `ISO_AGENT_BEDROCK_REGION_NAME` | Bedrock region override |
| `ISO_AGENT_BEDROCK_MAX_TOKENS` | Optional max tokens |
| `ISO_AGENT_PERPLEXITY_TRANSPORT` | `disabled` (default) \| `docker` — researcher MCP |
| `ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT` | **`disabled`** in **`Settings`** (non-CLI). **`iso-neuuf-coordinator`** sets **`stdio`** in **`os.environ`** when the var is absent from the process env **and** not assigned on an uncommented **`.env`** line (cwd) — **required** for any Google Drive/Sheets/Docs/etc. tools on the coordinator; **`google_workspace_mcp_*`** via **`npx google-workspace-mcp serve`**. Set **`disabled`** only when you intentionally want **no** Google file tools |
| `ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY` | `true` (default) — append **`--read-only`** to **`serve`**; set **`false`** to allow MCP write tools |
| `ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG` | **`iso-neuuf-coordinator`** sets **`true`** in **`os.environ`** under the same “unset in shell and **`.env`**” rule. When enabled, only **`strands.tools.mcp`**, **`mcp`**, and **`iso_agent...google_workspace_mcp`** log at DEBUG to stderr (root is **not** raised — avoids boto/botocore/markdown noise and request signing detail on stderr). Set **`false`** / **`0`** / **`no`** to quiet |
| `ISO_AGENT_DRIVE_ENABLED` | For **`drive_tools`** tests / internal use only — **not** wired to the Neuuf coordinator |
| `ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS` | Same — allowlist for **`drive_tools`** tests |
| `ISO_AGENT_DRIVE_ALLOWED_FILE_IDS` | Same — optional file IDs for **`drive_tools`** tests |
| `ISO_AGENT_DRIVE_MAX_LIST` | Same — max list size (default 25, cap 100) |
| `ISO_AGENT_NOTION_ENABLED` | `true` (default) / `false` — opt out of Notion tools |
| `ISO_AGENT_NOTION_TRANSPORT` | `hybrid` (default) \| `mcp_primary` \| `rest_only` — `rest_only` disables coordinator Notion tools; MCP uses OAuth (`docs/NOTION_MCP.md`) |
| `ISO_AGENT_NOTION_ALLOWED_PARENT_IDS` | Comma-separated Notion **page** UUIDs (draft parents for ``notion_create_qms_draft``); merged with per-user ``memory/users/<user_key>/notion/allowlist.json`` |
| `ISO_AGENT_NOTION_ALLOWED_PAGE_IDS` | Comma-separated Notion **page** UUIDs readable via ``notion_read_page``; merged with the same persisted file |
| `ISO_AGENT_NOTION_DISCOVERY_ENABLED` | `true` (default) / `false` — hide ``notion_discover_connected_pages`` only |
| `ISO_AGENT_CHAT_WEBHOOK_SECRET` | Shared secret header value for Chat ingress |
| `ISO_AGENT_CHAT_ALLOW_INSECURE` | `true` only for local dev without secret |
| `ISO_AGENT_CHAT_DEDUPE_TTL_SECONDS` | Webhook dedupe window (seconds) |

## Runtime / process (usually non-secret)

| Variable | Purpose |
|----------|---------|
| `PORT` | `iso-chat-webhook` bind port (default 8080) |
| `UVICORN_LOG_LEVEL` | Uvicorn log level for webhook |
| `STRANDS_TOOL_CONSOLE_MODE` | Set by `iso-neuuf-coordinator` for richer CLI tool UI |
| `BYPASS_TOOL_CONSENT` | When `true`, `strands_tools` **`python_repl`**, **`editor`**, **`shell`** skip interactive `[y/*]` confirmation (Strands upstream). `iso-neuuf-coordinator` **setdefaults** this to `true` unless **`--require-tool-consent`**; not set by Google Chat ingress |

## Local files (do not commit)

| Path | Purpose |
|------|---------|
| `secrets/**/*.json` | Google (and similar) JSON keys — **gitignored** |
| `memory/users/**` | Per-user runtime state — gitignored except `.gitkeep` |
| `mcp_oauth.json` (repo root or cwd) | Notion MCP OAuth tokens — **gitignored**; see `docs/NOTION_MCP.md` |
| `.env` (optional) | pydantic-settings reads it if present — **gitignored** at repo root |

## Safe template in git

| Path | Purpose |
|------|---------|
| `.env.example` | **Committed** placeholder names and defaults — copy to `.env` and fill secrets locally (`cp .env.example .env`) |

## Copy-paste: Google Drive (this repo)

From the repository root, after placing your key under `secrets/google/`:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secrets/google/<YOUR_SERVICE_ACCOUNT>.json"
# ISO_AGENT_DRIVE_ENABLED defaults true; export ISO_AGENT_DRIVE_ENABLED=false to disable.
export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS="0AMWuWf-m9SwNUk9PVA"
```

Replace `<YOUR_SERVICE_ACCOUNT>.json` with your file under `secrets/google/`. **Folder allowlist** uses **`ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS`** (comma-separated). There is **no** `ISO_AGENT_DRIVE_FOLDER_ID` in this codebase.

See also **`docs/INTEGRATIONS_WALKTHROUGH.md`** (operator steps) and **`secrets/README.md`** (local file layout).
