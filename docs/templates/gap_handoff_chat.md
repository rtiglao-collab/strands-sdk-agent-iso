# Gap → Google Chat (draft handoff)

Use after **`gap_list_recent`** (or the JSON lines in `memory/users/<user_key>/gaps/gaps.jsonl`) when drafting with **`neuuf_comms`**.

**Suggested DM pattern**

- One gap per message thread when possible.
- Lead with **gap_id** and **title** from the record.
- Include **severity**, **suggested_owner_role**, and **summary** (short).
- If **iso_clause_refs** or **evidence_refs** are empty, say what evidence is still needed—do not invent links.
- Close with a concrete ask (confirm owner, due date, or point to the controlling doc).

**Example skeleton**

```text
[Follow-up: QMS gap {{gap_id}}]
Title: {{title}}
Severity: {{severity}} | Suggested owner role: {{suggested_owner_role}}
Summary: {{summary}}
Refs: {{iso_clause_refs}} | Evidence: {{evidence_refs}}
Ask: Can you confirm owner + target date, or point us to the latest controlled procedure?
```

Replace placeholders from the gap JSON; keep drafts **human-sendable** only (no auto-post in this phase).
