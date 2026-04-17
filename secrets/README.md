# Local secrets (development only)

Use this tree for **credential files that must never be committed**. Only markdown and `.gitkeep` files here are tracked in git; **`*.json` under `secrets/` is gitignored**.

## Google (Drive / APIs) — service account JSON

1. In [Google Cloud Console](https://console.cloud.google.com/), create a **service account** key (**JSON**).
2. Save the file inside this repo as:

   `secrets/google/<anything>.json`  
   Example: `secrets/google/neuuf-drive-dev.json`

3. Point the standard Google client env var at that path (absolute path is safest):

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secrets/google/neuuf-drive-dev.json"
   ```

The Drive integration reads **`GOOGLE_APPLICATION_CREDENTIALS`** (see `src/iso_agent/l3_runtime/integrations/drive_client.py`).

**Production:** use your platform’s secret manager or a mounted secret — do not rely on copying this folder layout into prod.
