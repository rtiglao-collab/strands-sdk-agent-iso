# Integrations walkthrough (Drive, Google Workspace MCP, Notion, Perplexity)

This document is an **operator guide**: what to create in each vendor console, which secrets to hold locally, and how to prove each integration works with the Neuuf coordinator (`iso-neuuf-coordinator`).

**Google Chat** (HTTP webhook) is documented in the root [`README.md`](../README.md) and can be wired later; CLI and local tools do not require it.

---

## 0. Python package extras

From the repo root with your venv active:

```bash
pip install -e ".[dev,drive,notion]"
```

- **`[drive]`** — Google API client libraries for `drive_list_folder` / `drive_read_document`.
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

## 2. Google Drive (read-only tools)

**What it does:** **`drive_list_folder`** and **`drive_read_document`** on the coordinator, **allowlist-enforced** (folder IDs and optional file IDs). No write/delete APIs in this product path.

### 2.1 Acquire (Google Cloud)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and select or create a **project**.
2. **APIs & Services → Library** → enable **Google Drive API**.
3. **APIs & Services → Credentials → Create credentials → Service account.**
   - Name it e.g. `iso-agent-drive-readonly`.
   - Grant **no** broad owner roles; Drive access is via **sharing**, not IAM “Drive admin” (unless your org uses domain-wide delegation—this walkthrough uses **file/folder sharing** to the SA email, which is simpler).
4. **Keys → Add key → JSON** → save the file to a **gitignored** path. Options:
   - **Inside this clone (local dev):** `secrets/google/your-name.json` — see **`secrets/README.md`** (`*.json` under `secrets/` is ignored by git).
   - **Outside the repo:** e.g. `~/secrets/iso-drive-sa.json`.

### 2.2 Share content with the service account

1. Open the JSON and find **`client_email`** (ends with `gserviceaccount.com`).
2. In Google Drive UI, share the **folders** (and optionally specific files) your agent must read with that **client_email** (Viewer is enough).
3. Collect **Folder ID** from the browser URL when the folder is open:
   `https://drive.google.com/drive/folders/<FOLDER_ID>`
   For a file:
   `https://drive.google.com/file/d/<FILE_ID>/view`

### 2.3 Environment variables

```bash
# Option A — key inside this clone (see secrets/README.md; *.json under secrets/ is gitignored):
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secrets/google/<YOUR_SERVICE_ACCOUNT>.json"
# Option B — key outside the repo:
# export GOOGLE_APPLICATION_CREDENTIALS="$HOME/secrets/iso-drive-sa.json"

# ISO_AGENT_DRIVE_ENABLED defaults true; omit or set false to disable Drive tools.
# Comma-separated Google Drive folder IDs (allowlist). There is no ISO_AGENT_DRIVE_FOLDER_ID.
export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS='folder_id_one,folder_id_two'
# Optional: allow reading specific files by ID even if parent logic differs
# export ISO_AGENT_DRIVE_ALLOWED_FILE_IDS='file_id_one'
# Optional:
# export ISO_AGENT_DRIVE_MAX_LIST=25
```

### 2.4 Verify

```bash
iso-neuuf-coordinator --query "Use drive_list_folder on an allowlisted folder and print up to 5 file names."
iso-neuuf-coordinator --query "Use drive_read_document on file ID <allowlisted file id> and return the first 400 characters of extracted text."
```

**Pass:** listing and read succeed for allowlisted IDs.
**Fail:** permission or “not allowlisted” — fix sharing or env comma lists (no spaces unless your parser allows—use comma-separated IDs as in README).

**Fail:** HTTP 403 / `accessNotConfigured` / “Google Drive API has not been used in project …” — the **Drive API is off** for the GCP project that owns this service account key. In Google Cloud Console: **APIs & Services → Library → Google Drive API → Enable**, wait a few minutes, retry.

---

## 2.5 Google Workspace MCP (optional stdio)

**What it does:** When **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio`**, the coordinator merges prefixed **`google_workspace_mcp_*`** tools from the [`google-workspace-mcp`](https://www.npmjs.com/package/google-workspace-mcp) server (Docs, Sheets, Drive, Gmail, Calendar, and more per upstream). This path uses **user OAuth** via the MCP wizard. It is **separate** from **`drive_*`** service-account REST tools (allowlisted folders/files).

### 2.5.1 Machine prerequisites

- **Node.js** and **npm** on **`PATH`** so **`npx`** works.

### 2.5.2 One-time setup (order matters)

The wizard expects an **OAuth 2.0 Client ID** JSON from Google Cloud (**Desktop app** type), not the service-account key used for **`drive_*`**.

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

### 2.5.3 Environment variables

```bash
export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=stdio
# Default: append --read-only to serve (recommended). To allow MCP write tools:
# export ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY=false
```

To disable (default):

```bash
export ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT=disabled
```

### 2.5.4 First-run behavior

On coordinator build, the process runs **`npx -y google-workspace-mcp serve`** (plus **`--read-only`** unless **`ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY=false`**). **`npx`** may download the package once (needs network).

### 2.5.5 Verify

```bash
iso-neuuf-coordinator --query "List tool names that start with google_workspace_mcp_ (if any) and say in one sentence whether Google Workspace MCP is available."
```

**Pass:** tool list includes **`google_workspace_mcp_`** names and a short capability summary.
**Fail:** logs show **`google_workspace_mcp=startup_failed`** — check Node/npm, completed **`setup`**, and network/npm allowlists.

**Coexistence:** **`drive_*`** still loads from **`GOOGLE_APPLICATION_CREDENTIALS`** + allowlists when configured; **`google_workspace_mcp_*`** follows the MCP OAuth user. Prefer one path per task to avoid confusing duplicate access.

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

**Script:** `python scripts/run_integration_smoke.py` runs discovery + Drive gap-file probe + Perplexity config (no LLM).

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

# Drive (optional)
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/secrets/iso-drive-sa.json"
# ISO_AGENT_DRIVE_ENABLED defaults true; omit or set false to disable Drive tools.
export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS='...'

# Google Workspace MCP (optional — user OAuth via npx google-workspace-mcp setup)
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
| Drive | `ISO_AGENT_DRIVE_*` in `Settings` | [`drive_tools.py`](../src/iso_agent/l3_runtime/tools/drive_tools.py) |
| Google Workspace MCP | `ISO_AGENT_GOOGLE_WORKSPACE_MCP_TRANSPORT`, `ISO_AGENT_GOOGLE_WORKSPACE_MCP_SERVE_READ_ONLY`; Node **`npx`**; OAuth via **`npx google-workspace-mcp setup`** | [`google_workspace_mcp.py`](../src/iso_agent/l3_runtime/integrations/google_workspace_mcp.py) → [`coordinator.py`](../src/iso_agent/l3_runtime/team/coordinator.py) |
| Notion | `ISO_AGENT_NOTION_*`, OAuth `mcp_oauth.json` (`docs/NOTION_MCP.md`); `NOTION_TOKEN` only for manual REST scripts | [`notion_tools.py`](../src/iso_agent/l3_runtime/tools/notion_tools.py), [`notion_mcp.py`](../src/iso_agent/l3_runtime/integrations/notion_mcp.py) |

---

## 6. Security reminders

- Keep JSON key files, **`mcp_oauth.json`**, and any **`NOTION_TOKEN`** used for debugging **out of git**; use a secrets manager in production.
- **Allowlists** are intentional for **strict full-page reads** and **draft parents**; **discovery** lists whatever pages are already shared with the integration in Notion.
- Rotate keys if leaked; update env on all hosts running `iso-chat-webhook` or workers.
