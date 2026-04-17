# Manual agent QA checklist (Neuuf coordinator CLI)

Use with:

```bash
cd /Users/Rj/strands-sdk-agent-iso && source .venv/bin/activate
iso-neuuf-coordinator
```

Or one-shot:

```bash
iso-neuuf-coordinator --query "<paste prompt below>"
```

Check the terminal for `Tool #N: <tool_name>` lines. Adjust placeholders (`<...>`) before running.

---

## 0. Preconditions

| Check | You need |
|-------|-----------|
| LLM | **Bedrock only**: AWS creds + region; optional `ISO_AGENT_BEDROCK_MODEL_ID` / `ISO_AGENT_BEDROCK_REGION_NAME` |
| Perplexity MCP | `PERPLEXITY_API_KEY` + `ISO_AGENT_PERPLEXITY_TRANSPORT=docker` + Docker running |
| Drive | `GOOGLE_APPLICATION_CREDENTIALS` + `ISO_AGENT_DRIVE_ENABLED=true` + allowlists |
| Notion discovery | `NOTION_TOKEN` + `ISO_AGENT_NOTION_ENABLED=true` + `ISO_AGENT_NOTION_DISCOVERY_ENABLED=true` |
| Notion strict read | `ISO_AGENT_NOTION_ALLOWED_PAGE_IDS` and/or persisted allowlist via **`notion_allowlist_add_read_page`** |
| Notion drafts | `ISO_AGENT_NOTION_ALLOWED_PARENT_IDS` and/or **`notion_allowlist_add_draft_parent`** |

### Troubleshooting: “the model says a Notion/Drive tool is missing”

| Symptom | Cause | Fix |
|--------|--------|-----|
| **`notion_read_page`** returns **`no_read_allowlist`** (or **`notion_create_qms_draft`** returns **`no_draft_parent_allowlist`**) | Merged allowlist (env **∪** `memory/users/.../notion/allowlist.json`) is empty for that channel. | Call **`notion_allowlist_add_read_page`** / **`notion_allowlist_add_draft_parent`** after **`notion_discover_connected_pages`** (if discovery is on), or set the `ISO_AGENT_NOTION_ALLOWED_*` env vars. |
| `drive_list_folder` says **folder not allowlisted** | The folder id is not in `ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS` (or typo). | Add that folder id to the comma list, or use an id already in the list. Share the folder with the service account email. |
| **Perplexity / web** never used | `ISO_AGENT_PERPLEXITY_TRANSPORT` defaults to **disabled** or Docker not running. | `export ISO_AGENT_PERPLEXITY_TRANSPORT=docker` and start Docker; keep `PERPLEXITY_API_KEY`. |

---

## 1. Core

**Identity**

```
Reply in one sentence confirming you are the Neuuf ISO coordinator.
```

**Current time tool**

```
What is the current time? Use the current_time tool if it is available; otherwise say you cannot.
```

---

## 2. Specialists (one tool each)

**Researcher — model-only**

```
Use neuuf_researcher only. In two bullets, summarize what ISO 9001:2015 clause 4.1 is about. Do not use web search; general knowledge only.
```

**Researcher — with Perplexity MCP (when Docker + key enabled)**

```
Use neuuf_researcher only. In one short paragraph, name one reputable public source for ISO 9001:2015 scope requirements and say whether you used a web search tool by name.
```

**Governance**

```
Use neuuf_governance only.

Excerpt:
"""
Corrective actions must be initiated within 10 business days of nonconformance detection. Extensions require VP Quality approval documented in the CAPA log.
"""

Question: What gaps or risks do you see relative to control and evidence themes? Stay grounded in this excerpt only.
```

**Gap analyst**

```
Use neuuf_gap_analyst only. Scenario: Internal audit found training matrices missing for three contractors in Q1. Hypothesize process gaps and suggested owner roles. Do not invent company names.
```

**Comms**

```
Use neuuf_comms only. Draft a short DM to a process owner asking them to confirm the target close date for audit finding AF-12. Draft only; do not claim it was sent.
```

---

## 3. Gap persistence (JSONL)

**Analyst (optional setup)**

```
Use neuuf_gap_analyst only on: "Document approvals bypass the two-person rule in engineering." Keep under 120 words.
```

**Append row**

```
Call gap_append_record with title="Two-person rule bypass", summary="Engineering document approvals sometimes signed by one person.", severity="high", suggested_owner_role="Document control lead", iso_clause_refs="8.5.6", evidence_refs="".
```

**List recent**

```
Call gap_list_recent with limit 10.
```

**Comms from gaps (optional)**

```
Call gap_list_recent with limit 3. Then use neuuf_comms to draft a DM referencing the newest gap_id only. Draft only.
```

---

## 4. Calendar (local SQLite)

```
Use iso_calendar_create with date="2026-08-15 10:00", location="Conference room B", title="Quality council prep", description="Review open CAPAs and audit actions."
```

```
Use iso_calendar_agenda for day 2026-08-15.
```

---

## 5. Audits (local schedule)

```
Use audit_schedule_add with label="Annual internal QMS audit", cadence_days=365, audit_type="internal".
```

```
Call audit_upcoming_reminders with within_days=180.
```

*(If the model returns a schedule id, you can follow with `audit_mark_completed` in a second turn.)*

---

## 6. Google Drive (when enabled)

**List folder**

```
Use drive_list_folder with folder id <ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS first id> and rely on the default list size. Print file names only.
```

**Read document**

```
Use drive_read_document with file id <Google Doc or Sheet id under your allowlist> and max_chars 5000. Return the first 1200 characters of exported text only.
```

---

## 7. Notion

**Discovery (read-only)**

```
Call notion_discover_connected_pages with query "" and max_pages 20. Output a bullet list of page titles only.
```

**Strict read (allowlisted page id)**

```
Call notion_read_page with page id <uuid from ISO_AGENT_NOTION_ALLOWED_PAGE_IDS>. Return the first 800 characters of plain text.
```

**Draft child page (writes Notion — optional)**

```
Use notion_create_qms_draft with parent_page_id=<uuid from ISO_AGENT_NOTION_ALLOWED_PARENT_IDS>, title="Manual QA smoke", body="Single paragraph created from CLI checklist. Delete in Notion UI if not needed."
```

---

## 8. Tool inventory (sanity)

```
List every coordinator tool name you can invoke this session as a single comma-separated line with no spaces after commas.
```

---

## 9. Automated smoke (no LLM)

```bash
cd /Users/Rj/strands-sdk-agent-iso && source .venv/bin/activate
python scripts/run_integration_smoke.py
```

---

## Pass / fail quick notes

- **Fail auth:** missing or wrong API keys / token / SA JSON path.
- **Fail Drive allowlist:** `folder_not_allowlisted` or `file_not_allowlisted` — fix env IDs or share folder with SA email.
- **Fail Notion read:** `page_not_allowlisted` — add page UUID to `ISO_AGENT_NOTION_ALLOWED_PAGE_IDS` and share page with integration.
- **Fail Notion discovery empty:** connect pages to the integration in Notion UI.
- **Perplexity:** if logs show startup failure, check Docker and `ISO_AGENT_PERPLEXITY_TRANSPORT=docker`.
