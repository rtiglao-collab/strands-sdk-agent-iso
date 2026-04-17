# Knowledge (prompts and org context)

- **`agents/`** — Specialist and primary system prompt bodies (markdown). Load these from `l3_runtime/prompts.py` / `l3_runtime/team/`. Neuuf roles: `neuuf_coordinator.md`, `researcher.md`, `governance_evidence.md`, `gap_analyst.md`, `comms_coordinator.md`.
- Keep ISO / compliance claims evidence-backed; do not invent policy text here without source artifacts.

Version these files in git. Runtime-only user state belongs under `memory/users/`, not here.
