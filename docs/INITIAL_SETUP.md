# Initial setup (what was built)

This document records the **first bootstrap** of the `iso-agent` host repository: layered layout for a Strands-based app, Cursor guardrails, secret scanning, and a **self-updating infrastructure manifest**. Use it for onboarding and for proving what “version zero” contained.

## Goals that drove the layout

- **Flux-style layers** for clarity: L1 inbound/router, L2 per-user scope, L3 shared Strands runtime (agents, tools, graphs).
- **ISO 9001–oriented assistant behavior**: evidence-first, no fabricated compliance, capabilities truth, traceability—without turning the repo into a full QMS.
- **Security first**: secrets scanning, no secrets in code, identity from platform fields (enforced in rules and architecture text).
- **Minimal scope**: small diffs, extend existing files before adding parallel docs or code paths (**discovery-first**).
- **Self-updating inventory**: generated `docs/generated/INFRASTRUCTURE.md` + pre-commit drift check.

## Repository structure (conceptual)

| Area | Path | Purpose |
|------|------|---------|
| Application package | `src/iso_agent/` | Installable Python package |
| L1 | `src/iso_agent/l1_router/` | `InboundContext`, handlers (avoid import cycles in `__init__.py`) |
| L2 | `src/iso_agent/l2_user/` | `UserScope`, `memory/users/<user_key>/` layout |
| L3 | `src/iso_agent/l3_runtime/` | `Agent` factories, tools, specialists stub |
| MCP (local) | `src/iso_agent/mcp/stdio_server.py` | Stdio MCP sample tools |
| Scripts | `src/iso_agent/scripts/demo_calculator.py` | Demo entry wired to layers |
| Prompts | `knowledge/agents/*.md` | Stubs for primary / specialist prompts |
| Runtime memory | `memory/users/` | Gitignored user partitions (`.gitkeep` only) |
| Skills (optional) | `skills/README.md` | How to wire AgentSkills later |
| Upstream pointers | `references/` | `STRANDS_SDK.md` (local `sdk-python` path + reading order), `STRANDS_OFFICIAL_DOCS.md` (strandsagents.com examples + user guide hub), `STRANDS_AWS_INTRO_BLOG.md` (AWS announcement summary + link), copies of Strands `HOOKS` / MCP architecture docs |
| Human architecture | `docs/ARCHITECTURE.md` | Layer model, hooks, change habit |
| Capabilities template | `docs/CAPABILITIES.template.md` | Product truth template |
| Doc maintenance | `docs/DOC_MAINTENANCE.md` | When to regenerate, pre-commit, git requirement |
| Generated inventory | `docs/generated/INFRASTRUCTURE.md` | **Auto-generated** — scripts only |

## Packaging and tooling

- **`pyproject.toml`**: `setuptools`, `src/` layout, dependencies `strands-agents`, `strands-agents-tools`, `mcp[cli]`, `pydantic`, `pydantic-settings`; optional extras `openai`, `anthropic`; `dev` includes pytest, ruff, mypy, **pre-commit**.
- **Console scripts**: `iso-demo-calculator`, `iso-mcp-stdio`.
- **Tests**: `tests/` mirroring critical helpers (e.g. memory paths, sync script parsers).
- **`.vscode/tasks.json`**: “Sync repo docs”, “Pre-commit (all files)”.

## Cursor / AI guardrails

Rules live in **`.cursor/rules/*.mdc`** (YAML frontmatter: `alwaysApply` or `globs`):

| Rule file | Intent |
|-----------|--------|
| `discovery-first.mdc` | Review repo and stack before coding; extend existing md/code; stack then AWS then recommend new deps |
| `core-scope.mdc` | Minimal diffs, explicit scope, points at discovery-first |
| `security-first.mdc` | Secrets, least privilege, multi-tenant isolation, pre-commit awareness |
| `iso9001-product.mdc` | Evidence, no fake ISO claims, capabilities + INFRASTRUCTURE as traceability |
| `repo-maintenance.mdc` | Run `sync_repo_docs.py`, commit generated file, edit ARCHITECTURE when behavior changes |
| `python-strands.mdc` | L1/L2/L3 placement, Strands patterns, typing, logging note |
| `git-explicit-push.mdc` | Do not `git push` / `gh … --push` unless the user explicitly asks |

**`AGENTS.md`** at repo root indexes these for Cursor and humans.

## Secret scanning and pre-commit

- **`.pre-commit-config.yaml`**: `pre-commit-hooks` (EOF, whitespace, yaml, large files, private keys), **gitleaks** v8.26.0, local hook **`python scripts/sync_repo_docs.py --check`**.
- **`.gitleaksignore`**: placeholder for false positives.
- **Requirement**: `git` in the project root for `pre-commit install` to work (`git init` if needed).

## Doc sync script

- **`scripts/sync_repo_docs.py`**: Writes **`docs/generated/INFRASTRUCTURE.md`** (console scripts, optional dependency groups, `src/iso_agent` tree, manifest of tracked docs/rules). **Deterministic** (no wall-clock timestamp) so `--check` is stable.
- After layout or script changes: `python scripts/sync_repo_docs.py`, then commit the generated file.

## Other files touched during bootstrap

- **`README.md`**: setup, pre-commit, sync, Cursor pointer, git note.
- **`.kiro/settings/mcp.json`**: points MCP server at `python -m iso_agent.mcp.stdio_server` with repo `cwd`.
- **Root `agent.py` / `mcp_server.py`**: removed in favor of `src/iso_agent` + console scripts.

---

## LLM prompt — rebuild this bootstrap (copy everything below the line)

```text
You are working in an empty or nearly empty Python project directory that will become a small “agent host” app using the Strands Agents SDK (pip: strands-agents, strands-agents-tools). Implement the following bootstrap exactly in spirit: layered L1/L2/L3 package under src/iso_agent, minimal demo, MCP stdio sample, documentation, Cursor rules, pre-commit with gitleaks, and a deterministic doc generator that writes docs/generated/INFRASTRUCTURE.md and is enforced by pre-commit --check.

Constraints:
- Security first: no secrets in repo; document pre-commit + gitleaks; .gitleaksignore placeholder.
- Do not over-engineer: no full QMS; keep rules concise (separate .mdc files per concern).
- ISO 9001 orientation in rules only as “evidence-first, no fabricated compliance, capabilities truth, traceability via generated inventory”—not legal advice.
- Discovery-first: always-on Cursor rule to search repo, extend existing md/code, prefer pyproject stack and existing AWS usage (e.g. Bedrock via Strands) before recommending new deps; rule must tell assistants to read the **local sdk-python checkout** documented in references/STRANDS_SDK.md (absolute path + reading order; suggest Cursor multi-root).
- Avoid import cycles: l1_router/__init__.py must NOT import handler; document importing handler from iso_agent.l1_router.handler.
- Python 3.10+, setuptools src layout, package name iso_agent, project name iso-agent in pyproject.toml.
- dev optional extra: pytest, pytest-asyncio, ruff, mypy, pre-commit. mypy overrides for untyped strands_tools and botocore.
- Console scripts: iso-demo-calculator -> iso_agent.scripts.demo_calculator:main, iso-mcp-stdio -> iso_agent.mcp.stdio_server:main. Demo uses strands_tools.calculator, layers InboundContext -> UserScope -> handle_user_message -> Agent.
- L2: stable_user_key (hash prefix), memory under repo/memory/users/<user_key>/, UserScope.from_context.
- Directories: knowledge/agents/*.md stubs, skills/README.md, memory/README.md + memory/users/.gitkeep, references/STRANDS_SDK.md plus short copies of upstream Strands docs HOOKS and MCP_CLIENT_ARCHITECTURE (attribute upstream).
- docs/: ARCHITECTURE.md (layers, data flow, capability truth, generated inventory section, security hooks, change habit), CAPABILITIES.template.md, DOC_MAINTENANCE.md, and this INITIAL_SETUP.md narrative.
- scripts/sync_repo_docs.py: parse [project.scripts] and [project.optional-dependencies] keys only with regex so lines like mypy>= do not parse as keys; build ascii tree of src/iso_agent; manifest via git ls-files when available else directory walk for prefixes; no timestamp in output; --check compares to on-disk INFRASTRUCTURE.md.
- .pre-commit-config.yaml: pre-commit-hooks v5, gitleaks v8.26.0, local python hook sync script --check, pass_filenames false, always_run true.
- .cursor/rules: discovery-first.mdc, core-scope.mdc, security-first.mdc, iso9001-product.mdc, repo-maintenance.mdc, python-strands.mdc (globs src/**/*.py). AGENTS.md indexes them.
- .vscode/tasks.json for sync and pre-commit.
- .gitignore: venv, caches, memory/users/** with exception for .gitkeep.
- Tests: memory_layout tests; sync_repo_docs parser tests via importlib loading the script module.
- README: hatch-style commands using pip install -e ".[dev]", pre-commit install, python scripts/sync_repo_docs.py, note git required for pre-commit.

Deliverables: all files created, runnable pytest, ruff clean on src/tests/scripts, sync_repo_docs.py --check passes after generating INFRASTRUCTURE.md once. End with a short checklist the human can verify.
```
