# Upstream Strands Agents (Python SDK)

Canonical repository: `https://github.com/strands-agents/sdk-python`

## Local checkout (best-practice context for development)

Use this on-disk clone when implementing or reviewing Strands patterns (prefer reading real code over guessing):

**`/Users/Rj/sdk-python`**

In Cursor, add that directory to the **same workspace** (multi-root) alongside this repo when you want full SDK navigation and search. If the clone moves, update this path here only, then regenerate `docs/generated/INFRASTRUCTURE.md` if your process requires it (this file is under `references/` and is listed in the manifest).

Suggested reading order for this host layout (paths relative to that checkout):

1. `AGENTS.md` — contributor and AI patterns for the SDK repo  
2. `README.md` — install and quick start  
3. `src/strands/agent/agent.py` — `Agent` lifecycle  
4. `src/strands/tools/decorator.py` — `@tool`  
5. `docs/HOOKS.md` — audit and policy hooks  
6. `src/strands/session/` — session managers if you persist conversations  
7. `src/strands/multiagent/graph.py` — deterministic specialist pipelines  
8. `src/strands/tools/mcp/` — MCP client for connector-style integrations  
9. `src/strands/vended_plugins/skills/` — AgentSkills.io-style progressive disclosure  

Documentation site: `https://strandsagents.com/`

Install in *this* repo via PyPI packages `strands-agents` and optional extras (see `pyproject.toml`), not by copying `sdk-python` source.
