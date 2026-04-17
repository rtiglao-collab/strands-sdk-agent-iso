# Audit flow (Neuuf ISO agent — Phase 7)

This document describes how **on-disk** audit cadence and **local** calendar tools fit into Neuuf’s ISO-oriented workflow. It complements **`docs/CAPABILITIES.template.md`**: the runtime must not claim actions that only humans or external systems perform.

## 1. Cadence model (automated storage only)

- **`audit_schedule_add`** stores a recurring obligation under **`memory/users/<user_key>/audits/schedule.json`** (per `UserScope`).
- Each row has **`cadence_days`**, **`audit_type`** (`internal`, `external`, `management_review`, `other`), and optional **`last_completed_iso`** (`YYYY-MM-DD`).
- **`audit_mark_completed`** advances the baseline so **`audit_upcoming_reminders`** can flag **overdue** or **due within N days** entries.
- **Not automated:** sending calendar invites, booking rooms, or enforcing that an audit actually occurred—those remain **human** or **corporate systems**.

## 2. Local calendar (not Google Calendar)

- **`iso_calendar_*`** tools persist rows in **`memory/users/<user_key>/calendar/appointments.db`** (SQLite).
- Use them for **ISO meeting prep**, **audit debriefs**, and **reminder planning** textually coordinated with **`neuuf_comms`**.
- **Not automated:** sync to Google Workspace, attendee availability, or enterprise room resources.

## 3. Governance / ISO 9001:2015 alignment

- **`neuuf_governance`** compares **user-supplied** excerpts to themes and highlights gaps; it does **not** output clause-level “compliant / not compliant” without excerpt text in the same conversation.
- Certification status, registrar interpretation, and legal significance are **always human / CB**.

## 4. Suggested operating sequence

1. Register cadences with **`audit_schedule_add`** (e.g. internal audit every 365 days).
2. After each real-world audit event, run **`audit_mark_completed`** with the completion date.
3. Periodically run **`audit_upcoming_reminders`**, then **`neuuf_comms`** to draft owner DMs (still **draft-only** until a human sends them).
4. Optionally mirror key dates into **`iso_calendar_create`** for the same user scope so the coordinator can answer “what is scheduled this week?” from local data.

## 5. Evidence and CAPABILITIES

- Keep **`docs/CAPABILITIES.template.md`** (or product **`CAPABILITIES.md`**) aligned: list what is **file-backed automation** vs **human-only** so the model does not over-claim.
