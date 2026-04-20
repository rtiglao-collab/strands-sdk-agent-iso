# Local secrets (development only)

For **`ISO_AGENT_*`** defaults and other env names, start from **`.env.example`** in the repo root (`cp .env.example .env` — **`.env`** is gitignored).

Use this tree for **credential files that must never be committed**. Only markdown and `.gitkeep` files here are tracked in git; **`*.json` under `secrets/` is gitignored**.

## Google — Workspace MCP (Neuuf coordinator)

Neuuf reaches Google **only** through **Google Workspace MCP** (user OAuth, **`npx google-workspace-mcp setup`**). Follow **`docs/INTEGRATIONS_WALKTHROUGH.md`** §2; OAuth tokens live under your user profile (paths printed by the wizard), not necessarily under `secrets/`.

You **may** store a **Desktop OAuth client** JSON here if you want it gitignored, but the upstream wizard defaults to **`~/.google-mcp/credentials.json`**.

**Production:** use your platform’s secret manager or a mounted secret — do not rely on copying this folder layout into prod.
