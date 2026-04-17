# Strands Agents — AWS Open Source Blog (context)

**Canonical URL:** https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/

**Source:** AWS Open Source Blog, *Introducing Strands Agents, an Open Source AI Agents SDK* (Clare Liguori, 16 May 2025). This file is a **pointer and short summary** for this repo; read the post for full detail and diagrams.

## How to use this alongside this repository

- Keep **`references/STRANDS_SDK.md`** as the map to the **local `sdk-python` checkout** and SDK file reading order.
- Use **`references/STRANDS_OFFICIAL_DOCS.md`** for **strandsagents.com** tutorials and examples (multi-agent, graphs, MCP, deployment).
- Use **this post** for **product-level framing**: why Strands is model-driven, what belongs in model vs tools vs prompts, and how teams think about production patterns.

## Best-practice themes (from the post)

1. **Agent = model + tools + prompt** — the runtime loop is model-led (planning, tool choice, reflection) rather than heavy hand-authored orchestration for every branch.
2. **Tools are the main customization surface** — retrieval, APIs, AWS calls, static guidance, and patterns like “many tools, retrieve a subset” are expressed as tools the model can invoke.
3. **MCP** — Strands integrates MCP servers as tools; prefer MCP for connector-style capabilities where it fits.
4. **Multi-agent** — graphs, swarms, and workflow-style composition are part of the ecosystem for larger tasks; align specialist code with `l3_runtime/` and `references/STRANDS_SDK.md` reading order. For **worked web examples**, use **`references/STRANDS_OFFICIAL_DOCS.md`** (e.g. https://strandsagents.com/docs/examples/).
5. **Models** — Bedrock is a first-class path; other providers (Anthropic API, Ollama, OpenAI via LiteLLM, etc.) are described in the post as supported patterns—match what you actually install and configure in **`pyproject.toml`** / env for this host.
6. **Production** — the post outlines deployment shapes (local client, API behind Lambda/Fargate/EC2, isolated tool backends, return-of-control). Use **`docs/ARCHITECTURE.md`** for *this* app’s L1/L2/L3 split; use the post when reasoning about infra patterns Strands assumes.
7. **Observability** — OpenTelemetry-style instrumentation for trajectories and metrics is called out; wire OTEL when you add production paths, not in the bootstrap demo alone.

## Credentials and demos

Examples in the post (e.g. naming agent with `http_request` and an MCP server) assume **tokens and cloud access** where stated (e.g. `GITHUB_TOKEN`, Bedrock model access). Follow **`security-first`** in this repo: never commit secrets; use environment variables or a host secret store.
