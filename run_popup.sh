#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "/.flatpak-info" || -n "${FLATPAK_ID:-}" ]]; then
  exec flatpak-spawn --host bash -lc "cd '${SCRIPT_DIR}' && exec '${SCRIPT_DIR}/.venv/bin/python' -m src.transcriber_popup"
fi

exec "${SCRIPT_DIR}/.venv/bin/python" -m src.transcriber_popup
