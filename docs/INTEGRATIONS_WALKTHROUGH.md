# Integrations walkthrough (Google Workspace MCP, Notion, Perplexity)

This document is an **operator guide**: what to create in each vendor console, which secrets to hold locally, and how to prove each integration works with the Neuuf coordinator (`iso-neuuf-coordinator`).

**Google Chat** (HTTP webhook) is documented in the root [`README.md`](../README.md) and can be wired later; CLI and local tools do not require it.

---

## 0. Python package extras

From the repo root with your venv active:

```bash
pip install -e ".[dev,notion]"
```

- **`[notion]`** — `notion-client` for `notion_read_page` / `notion_create_qms_draft`.
- **`[dev]`** — pytest, ruff, mypy, FastAPI stack used elsewhere.

Perplexity uses **Docker** at runtime (no extra pip group beyond what pulls `mcp` already in base deps).

---

## 1. Perplexity (researcher MCP)

**What it does:** When configured, the coordinator’s **`neuuf_researcher`** tool attaches MCP tools from the official **`mcp/perplexity-ask`** Docker image so the inner researcher can run web-backed search. If unset, the researcher stays **model-only** (still works, no web guarantee).

### 1.1 Acquire

1. Create an account at [https://www.perplexity.ai](https://www.perplexity.ai) (or your org’s Perplexity workspace).
2. Open API / developer settings and create an **API key** (string starting with `pplx-` is typical). Store it in a password manager.

### 1.2 Machine prerequisites

- **Docker Desktop** (macOS/Windows) or Docker Engine on Linux, **running** (`docker ps` works without sudo if that is your policy).

### 1.3 Environment variables

```bash
export PERPLEXITY_API_KEY='pplx-...'   # not ISO_AGENT_ prefixed
export ISO_AGENT_PERPLEXITY_TRANSPORT=docker
```

To disable (default safe mode):

```bash
unset PERPLEXITY_API_KEY
export ISO_AGENT_PERPLEXITY_TRANSPORT=disabled
```

### 1.4 First-run behavior

On first coordinator build with valid settings, the process runs:

`docker run -i --rm -e PERPLEXITY_API_KEY mcp/perplexity-ask`

Docker will **pull** the image if missing (needs network once).

### 1.5 Verify

```bash
iso-neuuf-coordinator --query "Use neuuf_researcher only. List the tool names the researcher can call, then answer in one sentence whether web search is available."
```

**Pass:** narrative mentions MCP / search-style tools, or a successful short web-backed answer.
**Fail:** logs show `perplexity_mcp=startup_failed` — check Docker running, API key, and corporate Docker allowlists.

---

## 2. Google Workspace MCP (stdio — required for Google on Neuuf)

**What it does:** For **Drive, Sheets, Docs, Gmail, Calendar**, and other Google workspace surfaces, the Neuuf coordinator exposes prefixed **`google_workspace_mcp_*`** tools from the [`google-workspace-mcp`](https://www.npmjs.com/package/google-workspace-mcp) server when **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio`**. This path uses **user OAuth** via the MCP wizard.

### 2.1 Machine prerequisites

- **Node.js** and **npm** on **`PATH`** so **`npx`** works.

### 2.2 One-time setup (order matters)

The wizard expects an **OAuth 2.0 Client ID** JSON from Google Cloud (**Desktop app** type), not a **service account** JSON key.

1. **GCP — create the client file**
   In [Google Cloud Console](https://console.cloud.google.com/): pick a project → **APIs & Services → Library** → enable the APIs you need (the upstream wizard lists Docs, Drive, Sheets, Gmail, Calendar, Slides, Forms). Then **Credentials → Create credentials → OAuth client ID → Application type: Desktop** → download the JSON.

2. **Install the client secret on disk** (paths are what `npx google-workspace-mcp setup` prints):

   ```bash
   mkdir -p ~/.google-mcp
   cp /path/to/your-downloaded-client-secret.json ~/.google-mcp/credentials.json
   ```

   If **`❌ Credentials file NOT found at .../credentials.json`** appears, this step was skipped or the path/name is wrong.

3. **Run the MCP setup wizard** (account sign-in):

   ```bash
   npx google-workspace-mcp setup
   ```

4. Optional: **`npx google-workspace-mcp status`** to confirm readiness, or **`google-workspace-mcp accounts add <name>`** (per upstream help) after credentials exist.

Then set **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio`** and start **`iso-neuuf-coordinator`** so **`google_workspace_mcp_*`** tools load.

### 2.3 Environment variables

```bash
export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio
# Default: append --read-only to serve (recommended). To allow MCP write tools:
# export ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY=false
```

To disable (default):

```bash
export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=disabled
```

### 2.4 First-run behavior

On coordinator build, the process runs **`npx -y google-workspace-mcp serve`** (plus **`--read-only`** unless **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY=false`**). **`npx`** may download the package once (needs network).

### 2.5 Verify

```bash
iso-neuuf-coordinator --query "List tool names that start with google_workspace_mcp_ (if any) and say in one sentence whether Google Workspace MCP is available."
```

**Pass:** tool list includes **`google_workspace_mcp_`** names and a short capability summary.
**Fail:** logs show **`google_workspace_mcp=startup_failed`** — check Node/npm, completed **`setup`**, and network/npm allowlists.

**Coordinator Google tools:** To use Google from Neuuf, you **must** run **Workspace MCP** with **`stdio`** (default for **`iso-neuuf-coordinator`** when unset) and complete OAuth — **`google_workspace_mcp_*`** is the **only** Google file path. With **`disabled`**, there are **no** Google file tools.

### 2.6 Doc vs Sheet vs Excel (identify type before reading)

1. **Identify first:** From the user’s **full URL** or explicit wording, decide **Google Doc**, **Google Sheet**, or **Excel (`.xlsx`)** on Drive. Bare ids alone are ambiguous—**ask** or use an MCP **metadata** tool (if listed) before choosing a reader.
2. **Sheets** (`https://docs.google.com/spreadsheets/d/<id>/...`) → **spreadsheet** / **Sheets** MCP read tools, **not** **read Google Doc**.
3. **Docs** (`https://docs.google.com/document/d/<id>/...`) → **document** / **Doc** read tools.
4. **Excel files on Drive** → **Excel**-oriented MCP read tools (not Docs API).
5. If access still fails after the right tool, share with the **OAuth user** from **`accounts add`**, not a different Google account than the one bound to that label.

### 2.7 Debug MCP tool failures (see the real error)

Symptoms like **“not accessible”** from **`getDocumentInfo`** often mean the id is **not a Google Doc** (e.g. a **Sheet** or **Excel** file)—not Workspace “deny” on a correctly shared Doc.

- **`iso-neuuf-coordinator`** applies **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio`** and **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG=true`** when neither **the process environment** nor an **uncommented** assignment in **`.env`** (cwd) sets them (local testing). With debug on, **stderr** shows only **Strands MCP** and **`iso_agent` Google Workspace MCP** integration lines (not Bedrock/botocore/markdown-it). To opt out: `export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=disabled` and/or `export ISO_AGENT_GOOGLE_WORKSPACE_MCP_DEBUG=false`, or set the same keys in **`.env`**.
- Also run **`npx google-workspace-mcp status`** (and account list commands per upstream) outside the coordinator to confirm OAuth accounts.

### 2.8 Browser can open the file, but **`getDocumentInfo`** / **`readGoogleDoc`** fail

**This repo’s role:** The coordinator only spawns **`npx -y google-workspace-mcp serve`** with **`env=os.environ.copy()`** (same **`HOME`**, **`PATH`**, etc. as the Python process). It does **not** proxy Google APIs itself. Tool errors and messages like **“Document not found”** come from **upstream** + **Google’s APIs**, not from Strands allowlists.

**Do not confuse transports:** Lines like **`mcp.client.streamable_http`** on stderr are from **Notion’s hosted MCP** (HTTP/SSE) in the same process. **Google Workspace MCP** here is **stdio only**—those HTTP lines are **not** the Google server reconnecting.

**When both accounts “have access” in the browser but MCP says not found / not accessible:**

1. **Wrong API for the id** — **`getDocumentInfo`** is **Google Docs only**. If the URL is **`/spreadsheets/d/`**, **`/presentation/`**, or **`/file/d/`** (Excel, PDF, …), the Docs API returns **not found** even though Drive sharing looks fine. Use **`getSpreadsheetInfo`** / **`readSpreadsheet`**, **`readPresentation`**, **`getExcelInfo`**, or **`searchDrive`** (per your tool list) after checking the link path.
2. **`HOME` / token path** — OAuth files for **`npx google-workspace-mcp`** live under the user profile (see upstream **`setup`** output). If **`iso-neuuf-coordinator`** is launched from **Cursor, launchd, or a service** with a different **`HOME`** than the terminal where you ran **`accounts add`**, the child **`npx`** process may load **different or empty** tokens. Check the coordinator log line **`google_workspace_mcp=ready`** for **`home=`** and **`cwd=`** and compare to the shell where **`npx google-workspace-mcp status`** succeeds.
3. **Label vs Google identity** — **`account`** in each tool is the **local label** from **`accounts add`**, not an email. Confirm **`listAccounts`** and upstream **`status`** show the same identities you use in the browser.
4. **Shared drives / Workspace quirks** — Some upstream versions had edge cases for **Shared drives** or **converted** files; see the **`google-workspace-mcp`** repo’s troubleshooting and **`status --diagnose`** (or equivalent) if documented there.
5. **API 403 vs “sharing”** — Upstream maps Google **403** to messages like **“permission denied”** or **“no read access.”** That is **not always** “Share with this email.” It can mean **OAuth consent / stale token**, **Workspace admin blocking the OAuth client**, or other policy. Run **`npx google-workspace-mcp status`** (and **`accounts`** / **`setup`** per upstream) from the **same** shell **`HOME`** as the coordinator log line **`google_workspace_mcp=ready`** shows.

### 2.9 Sheet opens in the browser, but **`getSpreadsheetInfo`** / **`readSpreadsheet`** still say no access

The API only sees the **Google identity tied to the OAuth token** for your label (e.g. **`neuuf-info`**). “I can open it” in Chrome is irrelevant if that window is signed in as **someone else**.

1. **Resolve the exact Google identity** — In the coordinator, use **`google_workspace_mcp__listAccounts`** and read the **Email:** line for **`neuuf-info`** if present. From a shell: **`npx google-workspace-mcp accounts list`**. If **no email** is printed, run **`npx google-workspace-mcp accounts test-permissions neuuf-info`** (or re-complete OAuth for that label) so you know which user the token represents before fixing sharing.
2. **Share the file to that email** — In the Sheet → **Share**, add **that** address (Viewer or Editor). Groups and “anyone with the link” do **not** substitute if your Workspace blocks link access for API clients or external users.
3. **Wrong Chrome profile** — OAuth may have completed as **`bob@gmail.com`** while you usually use **`alice@company.com`** in the tab where the sheet works. Either share the sheet with **`bob`**, or remove **`neuuf-info`** and **`accounts add neuuf-info`** again while logged into Chrome as **`alice`**.
4. **Prove Sheets API for that token** — **`npx google-workspace-mcp accounts test-permissions neuuf-info`**. If **Sheets** fails here, sharing alone will not fix it until OAuth, scopes, or **Workspace admin** policy (third-party API / Drive restrictions) is corrected.

---

## 3. Notion (discovery read + strict full-page read + draft)

**What it does:**

- **`notion_discover_connected_pages`** (read-only) — **on by default**; lists pages your **OAuth session** can reach via Notion MCP search (id, title, parent, url). Set **`ISO_AGENT_NOTION_DISCOVERY_ENABLED=false`** to hide this tool.
- **`notion_read_page`** — full plain-text read for pages in the **merged** allowlist: **`ISO_AGENT_NOTION_ALLOWED_PAGE_IDS`** **∪** ids persisted for this user in **`memory/users/<user_key>/notion/allowlist.json`** (maintain via **`notion_allowlist_*`** tools).
- **`notion_create_qms_draft`** — creates `[DRAFT]` children only under **merged** draft parents: **`ISO_AGENT_NOTION_ALLOWED_PARENT_IDS`** **∪** persisted parent ids in the same JSON file.
- **`notion_refresh_page_index`** / **`notion_search_page_index`** / **`notion_page_index_status`** — persist a per-user title→id snapshot under **`memory/users/<user_key>/notion/`** for quick lookup without pasting UUIDs into every user message.
- **`notion_list_draft_parents`** — prints merged draft parent ids with titles from that index (refresh first if titles are missing).
- **`notion_list_pages_under_parent`** — lists **direct child** pages already present in the index under a parent you identify by **`parent_title_substring`** (unique among merged draft parents **and** merged read pages) or by **`parent_page_id`** (must still be allowlisted as read or draft parent).
- **`notion_create_qms_draft_for_parent_title`** — same as **`notion_create_qms_draft`** but resolves the draft parent by a **unique** title substring against merged draft parents (no raw UUID in the human prompt when titles are distinctive).
- **`notion_bootstrap_draft_parent_choices`** — numbered list from the index (workspace-top-level sorts first) when **no draft parents** are configured yet; optional **`search_text`** filters titles.
- **`notion_allowlist_add_draft_parent_by_choice`** — adds the draft parent for **choice=1..N** from the latest bootstrap list; **`search_text`** and **`max_options`** must match that bootstrap call exactly.

Optional Drive evidence line in the draft body when your prompt supplies a link.

### 3.1 Acquire (Notion)

1. Complete **OAuth** as in §3.5 so **`memory/users/<user_key>/notion/mcp_oauth.json`** exists for the CLI’s `user_key`.
2. The signed-in Notion user must be able to **open** target pages in the browser; MCP visibility follows that user’s workspace access.
3. (Optional) For ad-hoc REST debugging only, create an **internal integration**, set **`NOTION_TOKEN`**, and use **`tests/manual_notion_page_inspect.py`** — this is **not** what **`iso-neuuf-coordinator`** uses for **`notion_*`** tools.

### 3.2 Collect page UUIDs

From a Notion page URL:

`https://www.notion.so/Your-Title-<UUID_WITH_OPTIONAL_DASHES>`

The 32-character hex UUID (**with or without hyphens** in env vars — both normalize to the same id) goes into allowlists.

Decide:

- **Discovery:** enabled by default; use **`notion_discover_connected_pages`** for listing without pasting every page id in env. Set **`ISO_AGENT_NOTION_DISCOVERY_ENABLED=false`** only if you want to hide the discover tool.
- **`ISO_AGENT_NOTION_ALLOWED_PAGE_IDS`** — optional extra read ids (often empty if you use **`notion_allowlist_add_read_page`** from discovery).
- **`ISO_AGENT_NOTION_ALLOWED_PARENT_IDS`** — optional extra draft parents (often empty if you use **`notion_allowlist_add_draft_parent`**).
- **Persisted allowlist:** the coordinator can write **`notion/allowlist.json`** under the user’s **`memory/users/<user_key>/`** tree; it is **unioned** with the env vars and survives restarts without shell `export` churn.

### 3.3 Environment variables

```bash
# ISO_AGENT_NOTION_ENABLED defaults true; use false to disable Notion tools.
# ISO_AGENT_NOTION_DISCOVERY_ENABLED defaults true (notion_discover_connected_pages).
# ISO_AGENT_NOTION_TRANSPORT defaults hybrid (MCP when mcp_oauth.json exists).
export ISO_AGENT_NOTION_ALLOWED_PAGE_IDS='uuid-one,uuid-two'
export ISO_AGENT_NOTION_ALLOWED_PARENT_IDS='uuid-parent-for-drafts'
```

You can enable discovery **without** env parent/page lists; use **`notion_allowlist_add_*`** (or set the env lists) before **`notion_read_page`** / **`notion_create_qms_draft`** will return content or create pages.

### 3.4 Verify (read-only first)

```bash
iso-neuuf-coordinator --query "Call notion_discover_connected_pages with query '' and max_pages 15. Summarize titles and parent types in a short list."
iso-neuuf-coordinator --query "Call notion_read_page on one allowlisted page UUID and return the first 500 characters."
```

Draft smoke (writes Notion) — **without pasting a parent UUID** once the index knows parent titles:

```bash
iso-neuuf-coordinator --query "Call notion_refresh_page_index with query '' then notion_list_draft_parents. Then notion_create_qms_draft_for_parent_title with parent_title_substring=<unique substring of your draft parent title>, title='ISO agent smoke', body='One paragraph.'"
```

Or with an explicit parent id (classic):

```bash
iso-neuuf-coordinator --query "Use notion_create_qms_draft with parent_page_id=<uuid>, title='ISO agent smoke', body='One paragraph.'"
```

**Pass:** discovery lists shared pages; allowlisted read returns content; draft appears under the allowlisted parent.
**Fail:** OAuth missing or expired; empty discovery → query too narrow or the signed-in user cannot see those pages; wrong UUID.

### 3.5 Notion hosted MCP (OAuth, required for coordinator tools)

The coordinator’s **`notion_*`** tools use **user OAuth** (PKCE + dynamic client registration). Raw **`notion_mcp_*`** tools from the server are also merged when OAuth is configured. From **`iso-neuuf-coordinator`** REPL you can ask the agent to call **`notion_mcp_oauth_interactive_login`** once instead of a separate login command.

1. Set transport to `hybrid` (default) or `mcp_primary` (avoid **`rest_only`**, which disables Notion tools).
2. Run **`iso-notion-mcp-login`** (or **`iso-neuuf-coordinator --notion-mcp-login`**) and finish the browser flow.
3. Restart or reload the coordinator; **`notion_*`** tools start the MCP session; extra tools appear with the **`notion_mcp_`** prefix.

See **`docs/NOTION_MCP.md`** for redirect URI defaults and the MCP ↔ **`notion_*`** mapping.

**Legacy:** `NOTION_TOKEN` is only for **`tests/manual_notion_page_inspect.py`** and other ad-hoc REST debugging—not for the coordinator **`notion_*`** path.

**Script:** `python scripts/run_integration_smoke.py` runs in-repo gap prompt check + Perplexity config + Notion discovery (no LLM). Google is verified separately via this §2 checklist and **`iso-neuuf-coordinator`**.

---

## 4. Putting it together (one shell profile block)

Example **local dev** block for `~/.zshrc` or a sourced `~/iso-agent.env` (**do not commit**):

```bash
# LLM (default: Bedrock — AWS credential chain + region, e.g. profile or env vars)
# export AWS_PROFILE=...   # or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY where appropriate
# export AWS_REGION=us-east-1
# Optional explicit inference profile / model id:
# export ISO_AGENT_BEDROCK_MODEL_ID='...'

# Perplexity MCP (optional)
export PERPLEXITY_API_KEY='pplx-...'
export ISO_AGENT_PERPLEXITY_TRANSPORT=docker

# Google Workspace MCP (required for Google file tools — user OAuth via npx google-workspace-mcp setup)
# export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio

# Notion (optional — OAuth via iso-notion-mcp-login; see docs/NOTION_MCP.md)
# export NOTION_TOKEN='secret_...'  # only for tests/manual_notion_page_inspect.py (REST)
# export ISO_AGENT_NOTION_DISCOVERY_ENABLED=false  # only if you want to hide discover
export ISO_AGENT_NOTION_ALLOWED_PAGE_IDS='...'
export ISO_AGENT_NOTION_ALLOWED_PARENT_IDS='...'
```

Reload: `source ~/iso-agent.env`, then `iso-neuuf-coordinator`.

---

## 5. Where this is enforced in code (for debugging)

| Integration | Settings / env | Tools |
|-------------|----------------|--------|
| Perplexity | [`src/iso_agent/config.py`](../src/iso_agent/config.py) `perplexity_transport`; `PERPLEXITY_API_KEY` | [`src/iso_agent/l3_runtime/integrations/perplexity.py`](../src/iso_agent/l3_runtime/integrations/perplexity.py) → [`researcher_tool.py`](../src/iso_agent/l3_runtime/team/researcher_tool.py) |
| Google Workspace MCP | `ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT`, `ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY`; Node **`npx`**; OAuth via **`npx google-workspace-mcp setup`** — **only** Google file path on the Neuuf coordinator | [`google_workspace_mcp.py`](../src/iso_agent/l3_runtime/integrations/google_workspace_mcp.py) → [`coordinator.py`](../src/iso_agent/l3_runtime/team/coordinator.py) |
| Notion | `ISO_AGENT_NOTION_*`, OAuth `mcp_oauth.json` (`docs/NOTION_MCP.md`); `NOTION_TOKEN` only for manual REST scripts | [`notion_tools.py`](../src/iso_agent/l3_runtime/tools/notion_tools.py), [`notion_mcp.py`](../src/iso_agent/l3_runtime/integrations/notion_mcp.py) |

---

## 6. Security reminders

- Keep OAuth / token files (**`mcp_oauth.json`**, Google MCP wizard output under your profile), and any **`NOTION_TOKEN`** used for debugging **out of git**; use a secrets manager in production.
- **Allowlists** are intentional for **strict full-page reads** and **draft parents**; **discovery** lists whatever pages are already shared with the integration in Notion.
- Rotate keys if leaked; update env on all hosts running `iso-chat-webhook` or workers.
