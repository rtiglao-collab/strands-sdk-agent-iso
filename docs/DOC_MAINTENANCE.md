# Keeping docs and guardrails current

Before adding new markdown under `docs/`, check whether **`docs/ARCHITECTURE.md`**, **`docs/DOC_MAINTENANCE.md`**, **`docs/INITIAL_SETUP.md`**, or **`README.md`** should gain a section instead. Cursor rule **`discovery-first.mdc`** covers the same habit for code and docs.

Strands implementation patterns: **`references/STRANDS_SDK.md`** holds the **local `sdk-python` checkout path** and reading order—update only there if the clone moves.

Neuuf / ISO roadmap and sample mapping: **`docs/NEUUF_ISO_PHASE_PLAN.md`**, **`references/STRANDS_SAMPLES.md`**. Env/secrets handoff: **`docs/ENV_AND_SECRETS_INVENTORY.md`**. Perplexity MCP: **`src/iso_agent/l3_runtime/integrations/perplexity.py`**. Google Drive read-only: **`integrations/drive_client.py`**, **`tools/drive_tools.py`**. Notion QMS: **`integrations/notion_client.py`**, **`tools/notion_tools.py`**.

## Generated inventory (required)

`docs/generated/INFRASTRUCTURE.md` is **machine-generated**. It lists console scripts, optional dependency groups, the `src/iso_agent/` tree, and a manifest of tracked docs and rules.

After you add or remove packages, scripts, top-level docs, or `.cursor/rules`:

```bash
python scripts/sync_repo_docs.py
git add docs/generated/INFRASTRUCTURE.md
```

Pre-commit runs `python scripts/sync_repo_docs.py --check` and **blocks commits** if that file is stale.

## Hand-maintained docs

| File | You update when… |
|------|------------------|
| `docs/ARCHITECTURE.md` | Layering concepts or where new concerns live |
| `docs/ENV_AND_SECRETS_INVENTORY.md` | New integration env vars or secret-file paths |
| `docs/CAPABILITIES.template.md` → copy to `CAPABILITIES.md` | Product capabilities change |
| `.cursor/rules/*.mdc` | AI guardrails or conventions change |
| `AGENTS.md` | High-level entry points for assistants change |

Keep the generated file and hand-maintained architecture in sync: if the tree changes, regenerate first, then adjust `ARCHITECTURE.md` only if the mental model changed.

## Secret scanning

Gitleaks runs on **staged** changes via pre-commit. Install hooks in each clone:

```bash
pip install "iso-agent[dev]"
pre-commit install
```

`pre-commit` requires **git** in the project root. If hooks fail with “not a git repository”, run `git init` (or clone this project as a git repo).

If a finding is a false positive, add a scoped `.gitleaksignore` at the repo root (document why in the commit message).
