# Strands Agents — official documentation site (reference hub)

Use **https://strandsagents.com/** as the canonical **web** documentation alongside the **local `sdk-python` checkout** in **`references/STRANDS_SDK.md`** (read code for exact APIs; read the site for tutorials, deployment narratives, and worked examples).

This file is a **stable entry map**; deeper pages are linked from the sections below. Paths and titles can change upstream—if a link breaks, start from the site root or examples index and navigate.

## Primary entry points

| Resource | URL | Use when… |
|----------|-----|-----------|
| Site home | https://strandsagents.com/ | Orientation, news, navigation |
| **Examples overview** | https://strandsagents.com/docs/examples/ | **Index of runnable samples** (Python + TS tables): workflows, graphs, MCP, memory, multi-agent, structured output, multimodal, deployment pointers |
| User Guide (deploy, ops) | https://strandsagents.com/docs/user-guide/ | Production deployment guides (Bedrock AgentCore, Docker, Lambda, Fargate, App Runner, EC2, EKS, Kubernetes, etc.) and operating guidance linked from the examples page |
| **Amazon Bedrock (model provider)** | https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/ | **Canonical Strands path on AWS:** `BedrockModel`, boto3 credentials, IAM, `model_id`, troubleshooting — aligns with upstream `Agent()` defaulting to `BedrockModel` |

## Amazon Bedrock — Strands canonical path (not Bedrock Agents invoke)

Strands documents **native Bedrock integration** via **`BedrockModel`** (Bedrock Runtime **Converse**). A basic `Agent()` in upstream samples often defaults to a Claude-class **Bedrock** model id in supported regions; you override with whatever **Bedrock `model_id` / inference profile** your account can use — see the [Amazon Bedrock model provider](https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/) page.

**This host (`iso-agent`):** the shared factory **`src/iso_agent/l3_runtime/default_model.py`** constructs **`BedrockModel` only**. There is no stock path that calls Anthropic’s direct HTTP API; “which LLM” here means **which Bedrock-accessible FM** you declare (env / inference profile), still inside the Strands + AWS stack.

This is **not** the separate **Amazon Bedrock Agents** “invoke agent by id/alias” product unless you add a custom integration. For deployment platforms, the user guide also covers **Bedrock AgentCore** and other targets from the examples index.

## Examples hub — Python paths (from the official examples index)

Start at https://strandsagents.com/docs/examples/ and open the matching guide; direct links (use if still valid):

- **Structured output:** https://strandsagents.com/docs/examples/structured_output/
- **Agent workflows (sequential):** https://strandsagents.com/docs/examples/python/agents_workflows/
- **CLI reference agent:** https://strandsagents.com/docs/examples/python/cli-reference-agent/
- **File operations:** https://strandsagents.com/docs/examples/python/file_operations/
- **Graph loops / orchestration:** https://strandsagents.com/docs/examples/python/graph_loops_example/
- **Knowledge base agent:** https://strandsagents.com/docs/examples/python/knowledge_base_agent/
- **MCP calculator:** https://strandsagents.com/docs/examples/python/mcp_calculator/
- **Memory agent:** https://strandsagents.com/docs/examples/python/memory_agent/
- **Meta tooling:** https://strandsagents.com/docs/examples/python/meta_tooling/
- **Multi-agent:** https://strandsagents.com/docs/examples/python/multi_agent_example/multi_agent_example/
- **Multimodal:** https://strandsagents.com/docs/examples/python/multimodal/
- **Weather forecaster:** https://strandsagents.com/docs/examples/python/weather_forecaster/

## Deployment (user guide)

Linked from the examples overview as **Deployment Examples**; typical entry URLs include:

- https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_docker/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_aws_lambda/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_aws_fargate/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_aws_apprunner/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_amazon_ec2/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_amazon_eks/
- https://strandsagents.com/docs/user-guide/deploy/deploy_to_kubernetes/

Also follow **“Operating Agents in Production”** (linked from the examples page) for security, monitoring, and scaling themes.

## How this repo should use the site

- **Discovery / implementation:** Prefer patterns from **`references/STRANDS_SDK.md`** (local checkout) for API truth; use **strandsagents.com** examples for **end-to-end wiring** (especially **multi-agent**, **graphs**, **MCP**, **memory**, **structured output**).
- **This host’s layers:** map multi-agent and graph work to **`l3_runtime/`** and **`docs/ARCHITECTURE.md`**; keep L1/L2 concerns (identity, `UserScope`, paths) in this repo’s layers when porting an example.

## Related reference files

- **`references/STRANDS_SDK.md`** — GitHub `sdk-python` + local path + file reading order  
- **`references/STRANDS_AWS_INTRO_BLOG.md`** — AWS announcement summary (product framing)  
- **`references/HOOKS_from_strands_sdk.md`**, **`references/MCP_CLIENT_ARCHITECTURE_from_strands_sdk.md`** — upstream doc copies in this repo  

## Example sources on GitHub

The examples index instructs cloning **`https://github.com/strands-agents/docs`** and working under `docs/docs/examples` for runnable copies—use that when you need the full project tree next to this host.
