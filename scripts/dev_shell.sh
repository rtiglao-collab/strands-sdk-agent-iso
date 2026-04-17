#!/usr/bin/env bash
# Open a shell with repo venv + .env loaded (AWS, NOTION_TOKEN, etc.).
# Usage: source scripts/dev_shell.sh   OR   ./scripts/dev_shell.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/.venv/bin/activate"
  echo "dev_shell: activated ${ROOT}/.venv"
else
  echo "dev_shell: warning — no .venv at ${ROOT}/.venv (create with: python3 -m venv .venv && pip install -e '.[dev]')" >&2
fi

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ROOT}/.env"
  set +a
  echo "dev_shell: sourced ${ROOT}/.env"
else
  echo "dev_shell: no .env (optional: cp .env.example .env)" >&2
fi

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "dev_shell: starting ${SHELL:-bash} in ${ROOT} (exit to leave)"
  exec "${SHELL:-bash}"
fi
