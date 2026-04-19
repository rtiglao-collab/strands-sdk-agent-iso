# Capabilities (template)

Replace bracketed sections and delete items that are not implemented. The runtime and prompts should stay aligned with this file.

## Implemented

- [ ] Primary conversational agent (channel: …)
- [ ] Per-user memory root (`memory/users/<user_key>/`)
- [x] **Phase 1 — Neuuf coordinator** (`ISO_AGENT_PRIMARY_MODE=neuuf` or `iso-neuuf-coordinator`): coordinator + four specialist tools (research, governance, gap analyst, comms); prompts under `knowledge/agents/`
- [x] **Phase 2 — Perplexity MCP** (researcher): optional Docker `mcp/perplexity-ask` when `PERPLEXITY_API_KEY` + `ISO_AGENT_PERPLEXITY_TRANSPORT=docker`; otherwise model-only researcher
- [x] **Phase 3 — Google Drive read-only** (coordinator tools): service account + allowlisted folder/file ids; Docs/Sheets export as text
- [x] **Phase 4 — Notion QMS (draft + read)** — `notion_create_qms_draft` / `notion_read_page`; `NOTION_TOKEN` + allowlisted page UUIDs; optional hosted **Notion MCP** (`ISO_AGENT_NOTION_TRANSPORT`, `iso-notion-mcp-login`) — see `docs/NOTION_MCP.md`
- [x] **Phase 5 — Google Chat (HTTP webhook)** — `POST /google-chat` (FastAPI); DM vs shared-space prompt rules; optional `iso-agent[chat]`; secret header + env (see README)
- [x] **Phase 6 — Gap pipeline** — `gap_append_record` / `gap_list_recent`; append-only `memory/users/<user_key>/gaps/gaps.jsonl`; handoff templates in `docs/templates/`
- [x] **Phase 7 — Calendar / audits / governance** — `iso_calendar_*` (local DB per user), `audit_*` (cadence JSON), `current_time`; governance only clause-sharp when excerpts supplied; see `docs/AUDIT_FLOW.md`

### Automated vs human-only (Phase 7)

| Automated in-repo (per `user_key`) | Human-only / external |
|-----------------------------------|------------------------|
| `iso_calendar_*` rows in `memory/.../calendar/` | Google Calendar invites, room mailboxes, org scheduling systems |
| `audit_*` schedule file + reminder text | Whether an audit actually occurred; CB / registrar decisions |
| `neuuf_governance` gap analysis from **pasted** excerpts | Certification, legal “compliant” claims without evidence |

- [ ] Tools: …

## Not implemented yet

- [ ] …

## Async / long-running

Describe queues, workers, and how follow-ups are delivered to the user.
