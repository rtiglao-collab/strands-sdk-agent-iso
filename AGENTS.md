# AI assistant context (Cursor)

Persistent rules live in **`.cursor/rules/`** (`.mdc` files). Cursor loads them for this workspace.

**Always on:** discovery-first (`discovery-first.mdc`), scope discipline (`core-scope.mdc`), security (`security-first.mdc`), ISO-oriented product behavior (`iso9001-product.mdc`), repo maintenance (`repo-maintenance.mdc`).

**When editing Python under `src/`:** `python-strands.mdc` (layers, Strands usage, imports).

## Docs that must stay truthful

| Doc | Purpose |
|-----|---------|
| `docs/ARCHITECTURE.md` | Layering and where to add code (human-maintained) |
| `docs/generated/INFRASTRUCTURE.md` | **Auto-generated** inventory — run `python scripts/sync_repo_docs.py` after structural changes; never edit by hand |
| `docs/DOC_MAINTENANCE.md` | Checklist for regenerating docs and running hooks |
| `docs/INITIAL_SETUP.md` | Bootstrap narrative + LLM prompt to reproduce this repo’s initial layout |
| `docs/NEUUF_ISO_PHASE_PLAN.md` | Phased roadmap (Drive, Notion, Chat, Perplexity, gap pipeline) |
| `references/STRANDS_SAMPLES.md` | Local samples repo path + map sample → Neuuf use case |
| `src/iso_agent/l3_runtime/tools/drive_tools.py` | Phase 3 Drive read tools (allowlist + service account) |
| `src/iso_agent/l3_runtime/tools/notion_tools.py` | Phase 4 Notion QMS draft + read (allowlist + `NOTION_TOKEN`) |
| `src/iso_agent/l1_router/google_chat.py` + `adapters/google_chat_app.py` | Phase 5 Google Chat parse + HTTP webhook (`iso-chat-webhook`) |
| `src/iso_agent/l2_user/gap_store.py` + `l3_runtime/tools/gap_tools.py` | Phase 6 append-only gap JSONL + coordinator tools |
| `docs/templates/gap_handoff_*.md` | Phase 6 Chat / Notion draft patterns from gap records |
| `docs/AUDIT_FLOW.md` | Phase 7 audit cadence + local calendar boundaries vs human-only |
| `src/iso_agent/l2_user/calendar_store.py` + `l3_runtime/tools/calendar_tools.py` | Phase 7 per-user SQLite calendar |
| `src/iso_agent/l2_user/audit_schedule.py` + `l3_runtime/tools/audit_tools.py` | Phase 7 audit cadence JSON + reminder helpers |
| `docs/CAPABILITIES.template.md` | Copy to `CAPABILITIES.md` when you track real product capabilities |
| `src/iso_agent/l3_runtime/team/*_tool.py` + `specialist_base.py` | Neuuf specialists as tools (one module per specialist; `subagents.py` aggregates) |
| `src/iso_agent/l3_runtime/default_model.py` + `config.py` (`llm_provider`, Anthropic ids) | Default Anthropic Claude Sonnet; optional Bedrock via `ISO_AGENT_LLM_PROVIDER` |

Fill `docs/CAPABILITIES.template.md` (or a derived `CAPABILITIES.md`) so agent claims stay aligned with what is actually wired.

**Habit:** search the repo and read `docs/generated/INFRASTRUCTURE.md` before building; extend existing code and markdown where it fits—avoid duplicate docs and parallel implementations. Prefer the current stack (Strands, MCP, pydantic, existing AWS usage) before recommending new dependencies.

**Strands SDK context:** keep the upstream clone at **`references/STRANDS_SDK.md`** (local path + reading order) in scope—ideally open it in the **same Cursor workspace** (multi-root) as this repo when developing so searches and navigation include `src/strands/` best practices.

Do not treat this file as a substitute for the `.mdc` rules—keep those concise and current.
