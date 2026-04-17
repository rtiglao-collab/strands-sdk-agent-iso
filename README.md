# ISO agent host (Strands)

Layered layout for building a production-style agent: inbound routing (L1), per-user scope (L2), shared tools and agent runtime (L3). Strands stays an upstream dependency; this repo is your application shell.

## Layout

| Path | Role |
|------|------|
| `src/iso_agent/l1_router/` | Inbound events, identity-derived `user_key`, thread keys, “what runs next” |
| `src/iso_agent/l2_user/` | Per-user memory roots, session paths, profile helpers |
| `src/iso_agent/l3_runtime/` | `Agent` factories, specialist graphs, tool registration |
| `src/iso_agent/mcp/` | Optional stdio MCP server for local tools |
| `knowledge/` | System prompts and specialist prompt text (version in git) |
| `skills/` | AgentSkills.io-style skill folders (optional; wire via `AgentSkills` plugin) |
| `memory/` | Runtime user state (default gitignored under `memory/users/`; use your own policy) |
| `docs/` | Architecture and capability notes for *this* product |
| `references/` | Pointers to upstream Strands SDK docs and modules |

```text
strands-sdk-agent-iso/
├── docs/
├── knowledge/agents/
├── memory/users/
├── references/
├── skills/
├── src/iso_agent/
│   ├── l1_router/
│   ├── l2_user/
│   ├── l3_runtime/tools/
│   ├── mcp/
│   └── scripts/
├── tests/
└── pyproject.toml
```

## Setup

```bash
cd /Users/Rj/strands-sdk-agent-iso
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
python scripts/sync_repo_docs.py
```

`pre-commit` runs **gitleaks** (secret scanning), hygiene checks, and validates that **`docs/generated/INFRASTRUCTURE.md`** matches the repo layout. Regenerate that file with `python scripts/sync_repo_docs.py` whenever you add or move packages, scripts, or top-level docs or rules (see **`docs/DOC_MAINTENANCE.md`**).

**Note:** `pre-commit` expects a **git** repository in this directory (`git init` once if you have not already).

VS Code / Cursor: run the task **“Sync repo docs (INFRASTRUCTURE.md)”** from `.vscode/tasks.json`.

## Commands

- Demo calculator (Bedrock default unless you change the agent factory): `iso-demo-calculator` (see `iso_agent.l1_router.handler` for the L1 entrypoint)
- Local MCP stdio server: `iso-mcp-stdio`

## Model providers

Install one optional extra, for example:

```bash
pip install -e ".[openai]"
```

Then set model in `src/iso_agent/config.py` or environment variables you add there.

## Upstream SDK

This project does not vendor the Strands SDK. See `references/STRANDS_SDK.md` for the canonical repository and reading order.

## Cursor (AI) rules

See **`.cursor/rules/*.mdc`** and **`AGENTS.md`** for discovery-first review, scope, security, ISO-oriented behavior, repo maintenance (doc sync + hooks), and Python layout conventions.

**Bootstrap record:** **`docs/INITIAL_SETUP.md`** summarizes what was built initially and ends with an **LLM prompt** you can reuse to recreate the same setup elsewhere.

**Strands SDK on disk:** use the local clone path in **`references/STRANDS_SDK.md`** as the canonical place to read implementation patterns (`@tool`, hooks, MCP, multiagent). Add that folder to this Cursor workspace (multi-root) when you want full SDK context while editing `iso_agent`.
