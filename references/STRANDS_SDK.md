# Upstream Strands Agents (Python SDK)

Canonical repository: `https://github.com/strands-agents/sdk-python`

## Local checkout (best-practice context for development)

Use this on-disk clone when implementing or reviewing Strands patterns (prefer reading real code over guessing):

**`/Users/Rj/sdk-python`**

In Cursor, add that directory to the **same workspace** (multi-root) alongside this repo when you want full SDK navigation and search. If the clone moves, update this path here only, then regenerate `docs/generated/INFRASTRUCTURE.md` if your process requires it (this file is under `references/` and is listed in the manifest).

**Samples checkout (patterns and tutorials):** **`/Users/Rj/sdk-python/samples`** — see **`references/STRANDS_SAMPLES.md`** for a map from sample projects to Neuuf/ISO work.

## Official narrative (AWS)

For **Strands product framing and best-practice themes** (model + tools + prompt, model-driven loop, MCP, multi-agent, production and observability angles), read the AWS Open Source announcement and the companion summary in **`references/STRANDS_AWS_INTRO_BLOG.md`** (link: https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/).

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

**Official web docs (examples, user guide, deployment):** **`references/STRANDS_OFFICIAL_DOCS.md`** — hub starting at https://strandsagents.com/docs/examples/ and https://strandsagents.com/docs/user-guide/ (multi-agent, graphs, MCP, memory, structured output, deploy guides).

Install in *this* repo via PyPI packages `strands-agents` and optional extras (see `pyproject.toml`), not by copying `sdk-python` source.
