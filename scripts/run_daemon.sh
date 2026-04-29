#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "/.flatpak-info" || -n "${FLATPAK_ID:-}" ]]; then
  exec flatpak-spawn --host bash -lc "cd '${PROJECT_DIR}' && exec '${PROJECT_DIR}/.venv/bin/python' -m src.hotkey_daemon"
fi

exec "${PROJECT_DIR}/.venv/bin/python" -m src.hotkey_daemon
