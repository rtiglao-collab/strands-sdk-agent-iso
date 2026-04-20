# Before coding (iso-agent)

This block is **appended to the coordinator system prompt** whenever coding tools (`python_repl`, `editor`, `shell`, `journal`) are registered. Treat it as mandatory **pre-flight** before you write or execute code—not optional context.

## 1. Product and repo invariants

- **Layered host:** L1 router → L2 `memory/users/<user_key>/` → L3 tools under `src/iso_agent/`. Do not invent parallel layouts under **`~/`** or outside **`memory/`** for product state (Notion index, allowlists, gaps, etc.).
- **LLM:** This application uses **Amazon Bedrock only** (`get_default_model()`). Never assume or instruct **`ANTHROPIC_API_KEY`** or direct Anthropic API paths.
- **Notion:** Use **`notion_*`** coordinator tools and persisted files under **`memory/users/<user_key>/notion/`** (`allowlist.json`, `discovered_page_index.json`). Do not rebuild discovery or allowlists in **`python_repl`** when those tools exist. Never invent **`~/notion*.json`**, **`~/notion_index_lookup.py`**, or other home-directory “indexes”—those are not product state.
- **Delegation:** Research / web → **`neuuf_researcher`**. Policy text → **`neuuf_governance`**. Gaps → **`neuuf_gap_analyst`**. Comms drafts → **`neuuf_comms`**. Coding tools are for **this repo’s code and local execution**, not as a substitute for specialists.

## 2. Before `editor` or repo-wide `shell`

- Prefer **smallest change** that satisfies the user; match existing style and patterns in neighboring files.
- **Do not** add large new dependencies or new top-level directories without an explicit human ask aligned with **`AGENTS.md`** / **`docs/ARCHITECTURE.md`**.
- **New PyPI packages:** do not add arbitrary dependencies to **`pyproject.toml`** on your own. If the user explicitly asks to add a library to the product manifest, make the **smallest** change (optional extra group + version bounds) and mention **`python scripts/sync_repo_docs.py`** when the layout/extras list changes.
- After substantive Python edits, the human (or CI) runs **`hatch test`** / **`ruff`** / **`mypy`** from repo root—mention that if you cannot run them yourself.

## 3. Before `python_repl`

- Use the REPL for **short verification** or one-off inspection, not to replace **Notion**, **Drive**, or **MCP** tools.
- Do not **`exec(open(...))`** arbitrary paths the user did not supply; prefer tools and paths under **`memory/`** or the checked-out repo.

## 3.1 `ModuleNotFoundError` (missing pip packages)

- Prefer **stdlib** when it covers the job (`csv`, `json`, `xml.etree`, `zipfile`, etc.).
- For **Excel `.xlsx`**, the supported optional stack is **`openpyxl`** via the **`excel`** extra in **`pyproject.toml`** (see **`requirements-excel.txt`**). If import fails and the user’s task clearly needs spreadsheets, **do not** invent a substitute library—tell them once: from repo root, **`pip install -e ".[excel]"`** (or **`pip install -r requirements-excel.txt`**). When the user has **already** asked you to make the notebook/script work and installing deps is in scope, you may use **`shell`** from the **repo root** to run **`pip install -e ".[excel]"`** (needs network), then retry in **`python_repl`**. Do **not** `pip install` random PyPI names that are **not** already declared in **`pyproject.toml`** / **`requirements-*.txt`** without the user explicitly approving the package name.

## 4. After coding

- Summarize **what files or memory paths** changed (or that nothing changed) so the user can review in git or `memory/`.
