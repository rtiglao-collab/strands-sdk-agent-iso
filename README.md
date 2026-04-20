# ISO agent host (Strands)

Layered layout for building a production-style agent: inbound routing (L1), per-user scope (L2), shared tools and agent runtime (L3). Strands stays an upstream dependency; this repo is your application shell.

## Layout

| Path | Role |
|------|------|
| `src/iso_agent/l1_router/` | Inbound events, identity-derived `user_key`, thread keys, “what runs next” |
| `src/iso_agent/adapters/` | HTTP ingress (e.g. Google Chat webhook) |
| `src/iso_agent/l2_user/` | Per-user memory roots, session paths, profile helpers |
| `src/iso_agent/l3_runtime/` | `Agent` factories, specialist graphs, tool registration |
| `src/iso_agent/mcp/` | Optional stdio MCP server for local tools |
| `knowledge/` | System prompts and specialist prompt text (version in git) |
| `skills/` | AgentSkills.io-style skill folders (optional; wire via `AgentSkills` plugin) |
| `memory/` | Runtime user state (default gitignored under `memory/users/`; use your own policy) |
| `docs/` | Architecture and capability notes for *this* product |
| `references/` | Pointers to upstream Strands SDK docs and modules |

```text
strands-sdk-agent-iso/
├── docs/
├── knowledge/agents/
├── memory/users/
├── references/
├── skills/
├── src/iso_agent/
│   ├── adapters/
│   ├── l1_router/
│   ├── l2_user/
│   ├── l3_runtime/tools/
│   ├── mcp/
│   └── scripts/
├── tests/
└── pyproject.toml
```

## Setup

```bash
cd /Users/Rj/strands-sdk-agent-iso
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
python scripts/sync_repo_docs.py
```

`pre-commit` runs **gitleaks** (secret scanning), hygiene checks, and validates that **`docs/generated/INFRASTRUCTURE.md`** matches the repo layout. Regenerate that file with `python scripts/sync_repo_docs.py` whenever you add or move packages, scripts, or top-level docs or rules (see **`docs/DOC_MAINTENANCE.md`**).

**Before running `iso-neuuf-coordinator`:** the coordinator uses **Amazon Bedrock only** (`get_default_model()` always returns **`BedrockModel`**). Configure **AWS credentials** (and region) the usual way for boto3. Optional **`ISO_AGENT_BEDROCK_MODEL_ID`** / **`ISO_AGENT_BEDROCK_REGION_NAME`**. This repo **does not** call Anthropic’s direct HTTP API — use Claude (or other FMs) **through Bedrock** only. Policy: **`.cursor/rules/llm-bedrock-only.mdc`**.

**Note:** `pre-commit` expects a **git** repository in this directory (`git init` once if you have not already).

VS Code / Cursor: run the task **“Sync repo docs (INFRASTRUCTURE.md)”** from `.vscode/tasks.json`.

## Commands

- Demo calculator (Bedrock default unless you change the agent factory): `iso-demo-calculator` (see `iso_agent.l1_router.handler` for the L1 entrypoint)
- **Neuuf ISO coordinator (CLI):** `iso-neuuf-coordinator` — interactive REPL by default; **`--query "..."`** for a single turn. Unless **`--plain-console`**, sets **`STRANDS_TOOL_CONSOLE_MODE=enabled`** (Strands `samples/.../05-personal-assistant/` pattern). When **stdout is a TTY**, also wires a **Rich** callback so assistant replies stream as Markdown and tool starts get styled rules; **`--plain-console`** disables Rich and `STRANDS_TOOL_CONSOLE_MODE`. For **coding tools** (`python_repl`, `editor`, `shell`, `journal`), the CLI defaults **`BYPASS_TOOL_CONSENT=true`** (Strands convention) so the model can run them **without** blocking on a `[y/*]` tty prompt after every tool call; pass **`--require-tool-consent`** to restore those confirmations. Pass **`--no-coding-tools`** to omit coding tools for this session. **Google Chat** uses the same factory but passes **`include_coding_tools=False`**. **`handle_user_message`** does not set `BYPASS_TOOL_CONSENT`; export it yourself on trusted hosts if you enable coding tools there. Requires **AWS credentials** for **Amazon Bedrock**. Alternatively set `ISO_AGENT_PRIMARY_MODE=neuuf` and call `handle_user_message` from your own host code.
- Local MCP stdio server: `iso-mcp-stdio`
- **Google Chat (Phase 5):** `iso-chat-webhook` — requires `pip install -e ".[chat]"` or dev extras (FastAPI + uvicorn). Uses the **same** Neuuf coordinator stack as the CLI (`handle_google_chat_turn` → `build_neuuf_coordinator`); configure Chat’s HTTP target to `POST /google-chat` and forward **`x-iso-agent-chat-secret`** (see Chat section below).

### Coordinator: CLI vs Google Chat

| Path | When to use |
|------|-------------|
| **`iso-neuuf-coordinator`** | Local iteration, debugging prompts and tools with immediate stdin/stdout |
| **`iso-chat-webhook`** + Chat app | Real users in DM or spaces; uses ingress adapter + webhook secret + dedupe metrics |

Both execute the same L3 coordinator factory; only L1 (identity, thread, DM vs room rules) differs for Chat. **Coding tools** are on for CLI / in-process Neuuf; Chat wiring disables them at the factory (no env toggle).

## Model providers

**Only path:** **Amazon Bedrock** via **`BedrockModel()`** in **`get_default_model()`**. Configure the **AWS credential chain** and region; optional **`ISO_AGENT_BEDROCK_MODEL_ID`**, **`ISO_AGENT_BEDROCK_REGION_NAME`**, **`ISO_AGENT_BEDROCK_MAX_TOKENS`**. There is **no** `AnthropicModel`, **`ANTHROPIC_API_KEY`**, or direct Anthropic HTTP API in this application — use Claude **on Bedrock** when your account is entitled to that FM.

**OpenAI (optional extra):** `pip install -e ".[openai]"` only if you add a separate OpenAI-based factory in custom code (not the stock Neuuf path).

Settings live in **`src/iso_agent/config.py`** (`Settings` / `get_settings()`); the shared factory is **`src/iso_agent/l3_runtime/default_model.py`** (`get_default_model()`).

## Upstream SDK

This project does not vendor the Strands SDK. See `references/STRANDS_SDK.md` for the canonical repository and reading order.

## Cursor (AI) rules

See **`.cursor/rules/*.mdc`** and **`AGENTS.md`** for discovery-first review, scope, security, ISO-oriented behavior, repo maintenance (doc sync + hooks), and Python layout conventions.

**Bootstrap record:** **`docs/INITIAL_SETUP.md`** summarizes what was built initially and ends with an **LLM prompt** you can reuse to recreate the same setup elsewhere.

**Neuuf / ISO roadmap:** **`docs/NEUUF_ISO_PHASE_PLAN.md`** (phases for Drive, Notion, Google Chat, Perplexity, gap pipeline). **Samples map:** **`references/STRANDS_SAMPLES.md`** (`/Users/Rj/sdk-python/samples`).

**Integrations (acquire keys, env, verify):** **`docs/INTEGRATIONS_WALKTHROUGH.md`** — step-by-step Drive, Notion, and Perplexity; Chat remains in this README when you deploy ingress. Quick probe (no LLM): **`python scripts/run_integration_smoke.py`** (Drive gap-named file, Notion discovery, Perplexity config, in-repo gap prompt path).

**Perplexity (Phase 2):** set `PERPLEXITY_API_KEY` and `ISO_AGENT_PERPLEXITY_TRANSPORT=docker`, with Docker running, so the **researcher** sub-agent loads the `mcp/perplexity-ask` image (same pattern as `samples/.../05-personal-assistant/search_assistant.py`). Default transport is `disabled` so environments without Docker stay safe.

**Google Drive (Phase 3):** `pip install iso-agent[drive]`, set `GOOGLE_APPLICATION_CREDENTIALS` to a **service account JSON** with **Drive read-only** access. Drive tools are **enabled by default** (`ISO_AGENT_DRIVE_ENABLED` defaults **true**; set **`false`** to disable). Then configure:

- `ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS` — comma-separated folder IDs (listing + parent checks)
- Optional `ISO_AGENT_DRIVE_ALLOWED_FILE_IDS` — extra file IDs allowed for `drive_read_document`
- Optional `ISO_AGENT_DRIVE_MAX_LIST` (default 25, max 100)

The Neuuf coordinator gains **`drive_list_folder`**, **`drive_list_files`** (alias for the same list call), and **`drive_read_document`** tools (allowlist-enforced).

**Notion QMS (Phase 4):** `pip install iso-agent[notion]` (helpers / manual scripts). Coordinator **`notion_*`** tools use **hosted Notion MCP** after OAuth: run **`iso-notion-mcp-login`** or **`notion_mcp_oauth_interactive_login`** in the REPL so `memory/users/<user_key>/notion/mcp_oauth.json` exists. Set **`ISO_AGENT_NOTION_ENABLED=false`** to disable them. Set **`ISO_AGENT_NOTION_TRANSPORT=rest_only`** to skip Notion tools entirely.

- `ISO_AGENT_NOTION_ALLOWED_PARENT_IDS` — optional comma-separated **page** UUIDs where **`notion_create_qms_draft`** may create children (merged with per-user disk; see below)
- `ISO_AGENT_NOTION_ALLOWED_PAGE_IDS` — optional comma-separated **page** UUIDs readable via **`notion_read_page`** (merged with per-user disk)
- **`notion_discover_connected_pages`** (read-only search) is **on by default** when Notion tools load; set **`ISO_AGENT_NOTION_DISCOVERY_ENABLED=false`** to hide it. Use it to find ids, then persist with **`notion_allowlist_add_read_page`** / **`notion_allowlist_add_draft_parent`**. Persisted ids live in **`memory/users/<user_key>/notion/allowlist.json`** and are unioned with the env vars on every tool call.

Drafts include optional **Drive evidence** line when you pass `drive_link` into `notion_create_qms_draft`.

**Notion hosted MCP:** defaults to **`hybrid`** (`ISO_AGENT_NOTION_TRANSPORT`). **`notion_*`** tools call MCP under the hood when OAuth is configured—see **`docs/NOTION_MCP.md`**.

**Calendar & audits (Phase 7):** Per-user **local SQLite** calendar (`iso_calendar_*` under `memory/users/<user_key>/calendar/`) and **audit cadence** file (`audit_*` tools, `memory/.../audits/schedule.json`). **`current_time`** is on the coordinator for relative dates. **Not** Google Calendar or registrar automation—see **`docs/AUDIT_FLOW.md`**.

**Gap pipeline (Phase 6):** Coordinator tools **`gap_append_record`** and **`gap_list_recent`** write/read **`memory/users/<user_key>/gaps/gaps.jsonl`** (one JSON object per line). Use after **`neuuf_gap_analyst`** when the user wants durable gap rows; handoff patterns live in **`docs/templates/gap_handoff_chat.md`** and **`docs/templates/gap_handoff_notion.md`**.

**Google Chat (Phase 5):** `pip install iso-agent[chat]` (or use `.[dev]` which includes FastAPI + uvicorn for tests). Configure a Google Chat app **HTTP endpoint** pointing at your deployment’s `POST /google-chat`.

- **`ISO_AGENT_CHAT_WEBHOOK_SECRET`** — shared secret; each request must include header **`x-iso-agent-chat-secret`** with the same value (configure your proxy or Cloud Run to inject it).
- **`ISO_AGENT_CHAT_ALLOW_INSECURE=true`** — allows startup with **no** secret (local dev only; logs a warning).
- **`ISO_AGENT_CHAT_DEDUPE_TTL_SECONDS`** — in-memory duplicate-event window (default `300`, bounded `10..86400`) to tolerate webhook retries.
- Run: **`iso-chat-webhook`** (binds `0.0.0.0`, port from **`PORT`** default `8080`). **`GET /healthz`** for probes.
- **`GET /chat-metrics`** returns process-local in-memory counters (`received`, `duplicate`, `onboarding`, `parse_failed`, `turn_failed`, `turn_success`) for lightweight operational checks.
- Every response includes **`x-iso-agent-request-id`** (derived from inbound `x-iso-agent-request-id` / `x-request-id` when provided, else generated), and webhook logs include this ID for request correlation.
- **DM** (`space.type` `DM`) uses the full Neuuf coordinator; **shared rooms** (`ROOM` / `SPACE`) append stricter **`google_chat_room_suffix`** instructions (shorter, group-safe replies).
- **`ADDED_TO_SPACE`** events return a short onboarding message (no L3 turn execution).

**Strands SDK on disk:** use the local clone path in **`references/STRANDS_SDK.md`** as the canonical place to read implementation patterns (`@tool`, hooks, MCP, multiagent). Add that folder to this Cursor workspace (multi-root) when you want full SDK context while editing `iso_agent`.
