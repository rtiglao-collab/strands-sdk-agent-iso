# Strands samples repo (local)

**Path:** `/Users/Rj/sdk-python/samples`  
**Upstream:** `https://github.com/strands-agents/samples`

Use this alongside **`references/STRANDS_SDK.md`** (`/Users/Rj/sdk-python`) when designing agents. Samples are **educational**—mirror patterns in `iso_agent`, do not vendor sample code verbatim.

## Map: sample → Neuuf / ISO use

| Sample (under `02-samples/`) | Pattern | Neuuf / ISO application |
|------------------------------|---------|-------------------------|
| **`05-personal-assistant`** | Agents-as-tools coordinator; calendar; code agent; Perplexity MCP; **`STRANDS_TOOL_CONSOLE_MODE=enabled`** for readable tool traces in a terminal | **Primary model** for coordinator + researcher + coder; calendar for audit meetings; Perplexity MCP wired in **Phase 2** via `l3_runtime/integrations/perplexity.py` (Docker `mcp/perplexity-ask`, opt-in); Neuuf CLI mirrors the console-mode pattern |
| **`06-code-assistant`** | REPL / editor / shell | Internal automation, SOP generators, repo scripts (scoped) |
| **`14-research-agent`** | Research packaging | Deeper literature / standards research workflows (combine with Phase 2 MCP) |
| **`09-finance-assistant-swarm-agent`** | Swarm | Optional later for peer specialists (use only if graph is insufficient) |
| **`15-custom-orchestration-airline-assistant`** | Explicit orchestration | Gap → notify → schedule pipelines if not a simple graph |
| **`13-aws-audit-assistant`** | AWS-flavored audit assistant | Ideas for evidence trails and AWS-only tooling (adapt to Drive/Notion) |
| **`02-scrum-master-assistant`** | Backlog / process | Lightweight process nudges (not a full substitute for QMS) |

## Folders worth skimming first

- `01-tutorials/` — minimal Strands usage  
- `03-integrations/` — MCP and external patterns  
- `agent-patterns/` — bedrock swarms, code assistant variants  

## Cursor workspace

Add **`/Users/Rj/sdk-python/samples`** as a **multi-root** folder when you want search across sample + SDK + `iso_agent`.
