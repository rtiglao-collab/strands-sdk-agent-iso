# Neuuf ISO 9001 agent system — phased plan

This document is the **execution roadmap** for turning `iso-agent` into a coordinated team that supports ISO 9001–style operations for Neuuf: evidence from Google Drive, QMS structure in Notion, human loop via Google Chat, research, meetings, and governance. It maps **Strands samples** (`/Users/Rj/sdk-python/samples`) to our **L1 / L2 / L3** layout so we do not sprawl files or duplicate patterns.

## What we are building (target picture)

| Concern | Owner in architecture | Notes |
|--------|------------------------|--------|
| Inbound Google Chat (DM vs channel rules) | **L1** `google_chat.py` + **`adapters/google_chat_app`** | Identity from platform payload only |
| Per-user memory, reminders, profile | **L2** `UserScope` + `memory/users/` | Never cross `user_key` |
| Primary “personal assistant” coordinator | **L3** | Delegates to specialists (agents-as-tools pattern) |
| Research (Perplexity, citations) | **L3** specialist + MCP | Sample: `05-personal-assistant/search_assistant.py` |
| Self-coder / doc authoring | **L3** specialist + tools | Sample: `05-personal-assistant/code_assistant.py` |
| Read org docs (Drive), gap analysis | **L3** tools + specialist | New connectors; evidence-first |
| Notion QMS pages, SOPs, architecture | **L3** specialist + Notion API | Writes only with explicit scope |
| Gap detection → user outreach | **L3** graph or swarm | Two roles: scanner vs liaison |
| ISO meetings / audits | **L3** specialist + Calendar | Sample calendar tools in `05-personal-assistant` |
| Governance / clause review | **L3** specialist | Reads controlled text only; no fabricated clauses |
| Company Chat channel posts (e.g. new SOP) | **L3** tool | After human-approved content |

**Strands patterns to copy (not copy-paste files):**

- **Agents as tools** — `samples/02-samples/05-personal-assistant/` (`personal_assistant.py`, `code_assistant.py`, `search_assistant.py`): coordinator `Agent` with `@tool`-wrapped sub-agents.
- **Perplexity MCP** — same sample’s `search_assistant.py` + Docker MCP image; we adopt in Phase 2 with env-based config.
- **Swarm / graph** — when gap → liaison → meeting needs deterministic routing, use `GraphBuilder` (see `references/STRANDS_SDK.md` reading order: `multiagent/graph.py`); `09-finance-assistant-swarm-agent` for swarm inspiration once coordination is stable.
- **Custom orchestration** — `15-custom-orchestration-airline-assistant` if we need explicit state machine outside pure agents-as-tools.

## Phase 0 — Bootstrap (done)

Layered repo, Cursor rules, pre-commit, gitleaks, `sync_repo_docs.py`, `references/STRANDS_SDK.md` + local `sdk-python`, samples pointer.

## Phase 1 — In-repo coordinator team (stubs, no external SaaS) **done**

**Goal:** One **Neuuf coordinator** `Agent` per `UserScope`, with **four specialist sub-agents as tools** (empty or minimal tool lists), prompts under `knowledge/agents/`. Prove L3 wiring and `agents-as-tools` without Google/Notion/Chat.

**Deliverables:**

- `l3_runtime/team/` coordinator factory + `build_specialist_tools(scope)`.
- Prompts: `neuuf_coordinator`, `researcher`, `governance_evidence`, `gap_analyst`, `comms_coordinator`.
- `ISO_AGENT_PRIMARY_MODE=neuuf` switches L1 handler from demo calculator to coordinator (`Settings.primary_mode` in `iso_agent.config`).
- CLI: `iso-neuuf-coordinator` (one-shot or short loop).
- Tests: prompt loader + mode wiring.
- **Docs:** this file; `references/STRANDS_SAMPLES.md`; update `ARCHITECTURE.md` / `AGENTS.md` links.

**Exit criteria:** `pytest` green; coordinator runs locally with Bedrock (or configured model); no secrets in repo.

## Phase 2 — Research MCP (Perplexity) **done**

**Goal:** Researcher sub-agent uses Perplexity MCP when configured (Docker `mcp/perplexity-ask`); otherwise model-only fallback.

**Implemented:**

- `src/iso_agent/l3_runtime/integrations/perplexity.py` — singleton `MCPClient`, `get_perplexity_mcp_tools()`, `atexit` shutdown, test reset helper.
- `ISO_AGENT_PERPLEXITY_TRANSPORT=docker` **and** `PERPLEXITY_API_KEY` required to start MCP; default transport `disabled` so CI and laptops without Docker do not auto-pull.
- `l3_runtime/team/subagents.py` — researcher inner `Agent` receives MCP tools when available.
- Logging uses structured messages **without** secret values.

**Exit criteria:** Tests cover configured/disabled/fake client paths; `docs/CAPABILITIES.template.md` updated; README documents env vars.

## Phase 3 — Google Drive (read-only first) **done**

**Goal:** Coordinator gains **read-only** Drive tools: list allowlisted folders, export Google Docs/Sheets as text when parents (or explicit file ids) are allowlisted.

**Implemented:**

- Optional extra **`pip install iso-agent[drive]`** (`google-api-python-client`, `google-auth`).
- `src/iso_agent/l3_runtime/integrations/drive_client.py` — service account build, list children, metadata, export.
- `src/iso_agent/l3_runtime/tools/drive_tools.py` — `drive_list_folder`, `drive_read_document` tools merged in **`team/coordinator.py`**.
- Settings: `drive_enabled`, `drive_allowed_folder_ids`, `drive_allowed_file_ids`, `drive_max_list`; credentials via **`GOOGLE_APPLICATION_CREDENTIALS`** (standard path to service account JSON).
- **Allowlists required** before tools attach; no cross-folder reads without an allowlisted parent or file id.

**Exit criteria:** Tests mock the Drive service; docs and capability template updated; sanitized errors on failures.

## Phase 4 — Notion QMS **done**

**Goal:** Coordinator tools to **create draft child pages** under allowlisted parents and **read** allowlisted pages as plain text, with optional **Drive link** embedded in the draft body for traceability.

**Implemented:**

- Optional extra **`pip install iso-agent[notion]`** (`notion-client`).
- `src/iso_agent/l3_runtime/integrations/notion_client.py` — UUID validation, `create_child_page`, `fetch_page_text`.
- `src/iso_agent/l3_runtime/tools/notion_tools.py` — `notion_create_qms_draft`, `notion_read_page` (only if respective allowlists are non-empty).
- Token: **`NOTION_TOKEN`** (internal integration secret; not prefixed with `ISO_AGENT_` to match Notion docs). Never logged.
- Settings: `notion_enabled`, `notion_allowed_parent_ids`, `notion_allowed_page_ids`; merged in **`team/coordinator.py`**.
- Draft titles prefixed with **`[DRAFT]`**; no “publish” path in this phase.

**Exit criteria:** Tests mock Notion calls; docs and capability template updated.

## Phase 5 — Google Chat ingress/egress **done**

**Goal:** L1 adapter for Chat events: DM vs space rules, thread keys, reply to same thread. Main coordinator invoked with `InboundContext` → `UserScope`.

**Implemented:**

- `src/iso_agent/l1_router/google_chat.py` — `parse_google_chat_event`, `handle_google_chat_turn` (identity from payload; uses `message.thread` when present for continuity).
- `src/iso_agent/adapters/google_chat_app.py` — FastAPI `POST /google-chat` synchronous JSON `{"text": "..."}`; `GET /healthz`.
- Webhook auth: header **`x-iso-agent-chat-secret`** must match **`ISO_AGENT_CHAT_WEBHOOK_SECRET`**, or set **`ISO_AGENT_CHAT_ALLOW_INSECURE=true`** for local dev with no secret (logs a warning).
- `build_neuuf_coordinator(..., google_chat_mode="room")` appends **`knowledge/agents/google_chat_room_suffix.md`** for shared spaces; DMs use full coordinator prompt.
- Optional **`pip install iso-agent[chat]`**; console **`iso-chat-webhook`** (uvicorn, `PORT` default 8080).
- `InboundContext.space_kind`: `dm` | `space` | `dev` (local `inbound_dm` sets `dm`).

**Exit criteria:** DM and room paths invoke the Neuuf coordinator with correct scope/thread keys; shared rooms get stricter system appendix; tests cover parse + HTTP + secret behavior.

## Phase 6 — Gap pipeline (multi-step) **done**

**Goal:** `gap_analyst` (scheduled or on-demand) produces structured gap records → `comms_coordinator` / liaison tool drafts messages to owners; optional `GraphBuilder` pipeline later for deterministic routing.

**Implemented:**

- `src/iso_agent/l2_user/gap_store.py` — Pydantic **`GapRecord`**, append-only **`gaps/gaps.jsonl`** under each user’s **`memory_root`**, **`list_recent_gaps`**, **`recent_gaps_json`**.
- `src/iso_agent/l3_runtime/tools/gap_tools.py` — Coordinator tools **`gap_append_record`**, **`gap_list_recent`** (merged in **`team/coordinator.py`** after specialist tools).
- **`docs/templates/gap_handoff_chat.md`** and **`docs/templates/gap_handoff_notion.md`** — copy/paste patterns for **`neuuf_comms`** and **`notion_create_qms_draft`**.
- Prompts updated: **`neuuf_coordinator`**, **`gap_analyst`**, **`comms_coordinator`**.

**Exit criteria:** Append-only JSONL under `memory/users/<user_key>/gaps/` + Chat/Notion handoff templates; coordinator can persist then draft follow-ups.

## Phase 7 — Calendar / audits / governance **done**

**Goal:** Meeting scheduling (calendar tools pattern from `05-personal-assistant`); audit cadence reminders; governance specialist compares org text to ISO 9001:2015 **only with supplied clause excerpts** (no hallucinated compliance).

**Implemented:**

- `src/iso_agent/l2_user/calendar_store.py` — per-user SQLite **`calendar/appointments.db`** (create, list, day agenda, update by id).
- `src/iso_agent/l3_runtime/tools/calendar_tools.py` — **`iso_calendar_create`**, **`iso_calendar_list`**, **`iso_calendar_agenda`**, **`iso_calendar_update`**.
- `src/iso_agent/l2_user/audit_schedule.py` + **`audit_tools.py`** — **`audits/schedule.json`** cadence; **`audit_schedule_add`**, **`audit_schedule_list`**, **`audit_mark_completed`**, **`audit_upcoming_reminders`**.
- Coordinator merges calendar + audit tools and **`current_time`** from **`strands_tools`** (see `team/coordinator.py`).
- **`docs/AUDIT_FLOW.md`** — operating sequence and boundaries vs human-only work.
- **`knowledge/agents/governance_evidence.md`** — stricter clause / certification discipline.

**Exit criteria:** Documented audit flow; CAPABILITIES distinguishes automated (file-backed) vs human-only; governance prompt forbids invented clause compliance.

## Cross-cutting (every phase)

- Update **`docs/CAPABILITIES.template.md`** (or product `CAPABILITIES.md`) when behavior changes.
- Run **`python scripts/sync_repo_docs.py`** when tree or scripts change.
- **Security:** secrets in env/secret manager; gitleaks; least privilege on OAuth scopes.
- **ISO discipline:** evidence-first; unknown owner/due date explicit; no claiming integrations until wired.

## Open decisions (record answers as you go)

1. **Model provider:** Bedrock only vs multi-provider for sub-agents?
2. **Docker for MCP** in production vs stdio Perplexity on host?
3. **Notion** single workspace vs multi-database?
4. **Gap storage:** files under `memory/users/` vs external DB?

When these are decided, append a short “Decisions” subsection to **`docs/ARCHITECTURE.md`** (do not create a new doc unless necessary).
