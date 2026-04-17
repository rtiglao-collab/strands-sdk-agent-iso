# Environment variables and secret files (inventory)

Use this list when moving from **local exports** and **`secrets/`** files to **cloud** secret managers, CI variables, or mounted files. Names match what the code reads today (`src/iso_agent/config.py`, tools, adapters).

**Convention:** `ISO_AGENT_*` variables are loaded by `Settings` (see `config.py`). A few vendors use **standard names** without that prefix (`GOOGLE_APPLICATION_CREDENTIALS`, `NOTION_TOKEN`, `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY`).

## Secret values (treat as credentials in prod)

| Name | Type | Used by | Local pattern | Cloud migration |
|------|------|---------|---------------|-----------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Filesystem path to JSON | Drive client (`drive_client.py`) | `secrets/google/*.json` (gitignored) | Mount file or inject JSON into a volume; set env to path |
| `NOTION_TOKEN` | String | Notion tools | export / secret manager | Parameter store / vault secret |
| `ANTHROPIC_API_KEY` | String | `default_model.py` when `ISO_AGENT_LLM_PROVIDER=anthropic` | export | Secret manager |
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
| `ISO_AGENT_LLM_PROVIDER` | `bedrock` (default) \| `anthropic` |
| `ISO_AGENT_BEDROCK_MODEL_ID` | Bedrock model or inference profile id |
| `ISO_AGENT_BEDROCK_REGION_NAME` | Bedrock region override |
| `ISO_AGENT_BEDROCK_MAX_TOKENS` | Optional max tokens |
| `ISO_AGENT_ANTHROPIC_MODEL_ID` | Anthropic model id when using direct API |
| `ISO_AGENT_ANTHROPIC_MAX_TOKENS` | Anthropic max tokens |
| `ISO_AGENT_PERPLEXITY_TRANSPORT` | `disabled` (default) \| `docker` — researcher MCP |
| `ISO_AGENT_DRIVE_ENABLED` | `true` / `false` — enable Drive tools |
| `ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS` | Comma-separated **folder** IDs (allowlist). **Not** `ISO_AGENT_DRIVE_FOLDER_ID`. |
| `ISO_AGENT_DRIVE_ALLOWED_FILE_IDS` | Optional comma-separated **file** IDs |
| `ISO_AGENT_DRIVE_MAX_LIST` | Max list size (default 25, cap 100) |
| `ISO_AGENT_NOTION_ENABLED` | `true` / `false` |
| `ISO_AGENT_NOTION_ALLOWED_PARENT_IDS` | Comma-separated Notion **page** UUIDs (draft parents) |
| `ISO_AGENT_NOTION_ALLOWED_PAGE_IDS` | Comma-separated Notion **page** UUIDs (read) |
| `ISO_AGENT_CHAT_WEBHOOK_SECRET` | Shared secret header value for Chat ingress |
| `ISO_AGENT_CHAT_ALLOW_INSECURE` | `true` only for local dev without secret |
| `ISO_AGENT_CHAT_DEDUPE_TTL_SECONDS` | Webhook dedupe window (seconds) |

## Runtime / process (usually non-secret)

| Variable | Purpose |
|----------|---------|
| `PORT` | `iso-chat-webhook` bind port (default 8080) |
| `UVICORN_LOG_LEVEL` | Uvicorn log level for webhook |
| `STRANDS_TOOL_CONSOLE_MODE` | Set by `iso-neuuf-coordinator` for richer CLI tool UI |

## Local files (do not commit)

| Path | Purpose |
|------|---------|
| `secrets/**/*.json` | Google (and similar) JSON keys — **gitignored** |
| `memory/users/**` | Per-user runtime state — gitignored except `.gitkeep` |
| `.env` (optional) | pydantic-settings reads it if present — **gitignored** at repo root |

## Safe template in git

| Path | Purpose |
|------|---------|
| `.env.example` | **Committed** placeholder names and defaults — copy to `.env` and fill secrets locally (`cp .env.example .env`) |

## Copy-paste: Google Drive (this repo)

From the repository root, after placing your key under `secrets/google/`:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secrets/google/<YOUR_SERVICE_ACCOUNT>.json"
export ISO_AGENT_DRIVE_ENABLED=true
export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS="0AMWuWf-m9SwNUk9PVA"
```

Replace `<YOUR_SERVICE_ACCOUNT>.json` with your file under `secrets/google/`. **Folder allowlist** uses **`ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS`** (comma-separated). There is **no** `ISO_AGENT_DRIVE_FOLDER_ID` in this codebase.

See also **`docs/INTEGRATIONS_WALKTHROUGH.md`** (operator steps) and **`secrets/README.md`** (local file layout).
