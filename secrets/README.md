# Local secrets (development only)

For **`ISO_AGENT_*`** defaults and other env names, start from **`.env.example`** in the repo root (`cp .env.example .env` — **`.env`** is gitignored).

Use this tree for **credential files that must never be committed**. Only markdown and `.gitkeep` files here are tracked in git; **`*.json` under `secrets/` is gitignored**.

## Google (Drive / APIs) — service account JSON

1. In [Google Cloud Console](https://console.cloud.google.com/), create a **service account** key (**JSON**).
2. Save the file inside this repo as:

   `secrets/google/<anything>.json`  
   Example: `secrets/google/neuuf-drive-dev.json`

3. Point the standard Google client env var at that path (from repo root, `$PWD` is fine):

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secrets/google/<YOUR_KEY>.json"
   export ISO_AGENT_DRIVE_ENABLED=true
   export ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS="<comma_separated_folder_ids>"
   ```

   Drive tools use **`ISO_AGENT_DRIVE_ALLOWED_FOLDER_IDS`** (allowlist), not `ISO_AGENT_DRIVE_FOLDER_ID`.

4. Full variable list and cloud migration notes: **`docs/ENV_AND_SECRETS_INVENTORY.md`**.

The Drive integration reads **`GOOGLE_APPLICATION_CREDENTIALS`** (see `src/iso_agent/l3_runtime/integrations/drive_client.py`).

**Production:** use your platform’s secret manager or a mounted secret — do not rely on copying this folder layout into prod.
