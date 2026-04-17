# AI assistant context (Cursor)

Persistent rules live in **`.cursor/rules/`** (`.mdc` files). Cursor loads them for this workspace.

**Always on:** discovery-first (`discovery-first.mdc`), scope discipline (`core-scope.mdc`), security (`security-first.mdc`), ISO-oriented product behavior (`iso9001-product.mdc`), repo maintenance (`repo-maintenance.mdc`), git push only when asked (`git-explicit-push.mdc`).

**When editing Python under `src/`:** `python-strands.mdc` (layers, Strands usage, imports).

## Docs that must stay truthful

| Doc | Purpose |
|-----|---------|
| `docs/ARCHITECTURE.md` | Layering and where to add code (human-maintained) |
| `docs/generated/INFRASTRUCTURE.md` | **Auto-generated** inventory — run `python scripts/sync_repo_docs.py` after structural changes; never edit by hand |
| `docs/DOC_MAINTENANCE.md` | Checklist for regenerating docs and running hooks |
| `docs/INITIAL_SETUP.md` | Bootstrap narrative + LLM prompt to reproduce this repo’s initial layout |
| `docs/CAPABILITIES.template.md` | Copy to `CAPABILITIES.md` when you track real product capabilities |

Fill `docs/CAPABILITIES.template.md` (or a derived `CAPABILITIES.md`) so agent claims stay aligned with what is actually wired.

**Habit:** search the repo and read `docs/generated/INFRASTRUCTURE.md` before building; extend existing code and markdown where it fits—avoid duplicate docs and parallel implementations. Prefer the current stack (Strands, MCP, pydantic, existing AWS usage) before recommending new dependencies.

**Strands SDK context:** keep the upstream clone at **`references/STRANDS_SDK.md`** (local path + reading order) in scope—ideally open it in the **same Cursor workspace** (multi-root) as this repo when developing so searches and navigation include `src/strands/` best practices. For **model/tools/prompt framing and production-oriented Strands guidance**, also read **`references/STRANDS_AWS_INTRO_BLOG.md`** (summary + link to the [AWS Open Source Strands intro](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)).

Do not treat this file as a substitute for the `.mdc` rules—keep those concise and current.
