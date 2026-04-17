# Gap → Notion QMS (draft handoff)

Use when creating **`[DRAFT]`** pages via **`notion_create_qms_draft`** so each gap has traceability.

**Body template (Markdown)**

```markdown
## Gap record

- **gap_id:** {{gap_id}}
- **created_at:** {{created_at}}
- **severity:** {{severity}}
- **thread_key:** {{thread_key}}

### Title
{{title}}

### Summary
{{summary}}

### Suggested owner role
{{suggested_owner_role}}

### ISO / clause refs
{{iso_clause_refs}}

### Evidence refs (Drive, audits, etc.)
{{evidence_refs}}
```

**Workflow**

1. Have the coordinator call **`gap_list_recent`** (or read `gaps/gaps.jsonl`) for the user scope you are working in.
2. For each gap that needs a QMS artifact, call **`notion_create_qms_draft`** with `title` like `[DRAFT] Gap — {{title}}` and `body` filled from the template.
3. Keep allowlisted Notion parent IDs only; never create pages outside allowlists.
