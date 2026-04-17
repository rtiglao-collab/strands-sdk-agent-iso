# Integrations walkthrough (Drive, Notion, Perplexity)

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

export ISO_AGENT_DRIVE_ENABLED=true
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

## 3. Notion (discovery read + strict full-page read + draft)

**What it does:**

- **`notion_discover_connected_pages`** (read-only) — when **`ISO_AGENT_NOTION_DISCOVERY_ENABLED=true`**, lists pages the integration can access via Notion’s search API (id, title, parent, url). Scope is whatever you **shared with the integration** in the Notion UI.
- **`notion_read_page`** — full plain-text read for pages in the **merged** allowlist: **`ISO_AGENT_NOTION_ALLOWED_PAGE_IDS`** **∪** ids persisted for this user in **`memory/users/<user_key>/notion/allowlist.json`** (maintain via **`notion_allowlist_*`** tools).
- **`notion_create_qms_draft`** — creates `[DRAFT]` children only under **merged** draft parents: **`ISO_AGENT_NOTION_ALLOWED_PARENT_IDS`** **∪** persisted parent ids in the same JSON file.

Optional Drive evidence line in the draft body when your prompt supplies a link.

### 3.1 Acquire (Notion)

1. In Notion: **Settings & members → Connections → Develop or manage integrations → New integration**.
2. Type: **Internal** (typical for workspace-only). Name it e.g. `ISO Neuuf agent`.
3. Copy **Internal Integration Secret** — this is **`NOTION_TOKEN`** (starts with `secret_`). Never commit it.
4. **Share pages with the integration:** on each Notion page the agent must see in discovery, read in full, or use as a parent for drafts, use **⋯ → Connections →** connect your integration (or “Add connections” in newer UI). Without this, API calls return “not found” or empty discovery.

### 3.2 Collect page UUIDs

From a Notion page URL:

`https://www.notion.so/Your-Title-<UUID_WITH_OPTIONAL_DASHES>`

The 32-character hex UUID (**with or without hyphens** in env vars — both normalize to the same id) goes into allowlists.

Decide:

- **Discovery:** enable **`ISO_AGENT_NOTION_DISCOVERY_ENABLED=true`** for workspace-style listing without putting every page id in env.
- **`ISO_AGENT_NOTION_ALLOWED_PAGE_IDS`** — optional extra read ids (often empty if you use **`notion_allowlist_add_read_page`** from discovery).
- **`ISO_AGENT_NOTION_ALLOWED_PARENT_IDS`** — optional extra draft parents (often empty if you use **`notion_allowlist_add_draft_parent`**).
- **Persisted allowlist:** the coordinator can write **`notion/allowlist.json`** under the user’s **`memory/users/<user_key>/`** tree; it is **unioned** with the env vars and survives restarts without shell `export` churn.

### 3.3 Environment variables

```bash
export NOTION_TOKEN='secret_...'
export ISO_AGENT_NOTION_ENABLED=true
export ISO_AGENT_NOTION_DISCOVERY_ENABLED=true
export ISO_AGENT_NOTION_ALLOWED_PAGE_IDS='uuid-one,uuid-two'
export ISO_AGENT_NOTION_ALLOWED_PARENT_IDS='uuid-parent-for-drafts'
```

You can enable discovery **without** env parent/page lists; use **`notion_allowlist_add_*`** (or set the env lists) before **`notion_read_page`** / **`notion_create_qms_draft`** will return content or create pages.

### 3.4 Verify (read-only first)

```bash
iso-neuuf-coordinator --query "Call notion_discover_connected_pages with query '' and max_pages 15. Summarize titles and parent types in a short list."
iso-neuuf-coordinator --query "Call notion_read_page on one allowlisted page UUID and return the first 500 characters."
```

Draft smoke (writes Notion):

```bash
iso-neuuf-coordinator --query "Use notion_create_qms_draft with title '[DRAFT] ISO agent smoke' and a one-paragraph body."
```

**Pass:** discovery lists shared pages; allowlisted read returns content; draft appears under the allowlisted parent.  
**Fail:** 401 → token wrong; 404 / empty discovery → page not shared with integration or wrong UUID.

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
export ISO_AGENT_DRIVE_ENABLED=true
export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS='...'

# Notion (optional)
export NOTION_TOKEN='secret_...'
export ISO_AGENT_NOTION_ENABLED=true
export ISO_AGENT_NOTION_DISCOVERY_ENABLED=true
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
| Notion | `ISO_AGENT_NOTION_*`, `NOTION_TOKEN` | [`notion_tools.py`](../src/iso_agent/l3_runtime/tools/notion_tools.py) |

---

## 6. Security reminders

- Keep JSON key files and `NOTION_TOKEN` **out of git**; use a secrets manager in production.
- **Allowlists** are intentional for **strict full-page reads** and **draft parents**; **discovery** lists whatever pages are already shared with the integration in Notion.
- Rotate keys if leaked; update env on all hosts running `iso-chat-webhook` or workers.
