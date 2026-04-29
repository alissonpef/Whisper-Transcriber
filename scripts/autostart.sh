#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="/tmp/whisper-transcriber.log"
LOCK_FILE="/tmp/whisper_daemon.lock"
VENV_PY="${PROJECT_DIR}/.venv/bin/python"

if [[ -f "$LOCK_FILE" ]]; then
  PID="$(cat "$LOCK_FILE" 2>/dev/null)" || PID=""
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "[$(date)] daemon already running (PID $PID)" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE"
fi

echo "[$(date)] starting daemon" >> "$LOG_FILE"

if [[ ! -x "$VENV_PY" ]]; then
  echo "[$(date)] missing venv python at $VENV_PY" >> "$LOG_FILE"
  exit 1
fi

cd "$PROJECT_DIR"
"$VENV_PY" -m src.hotkey_daemon >> "$LOG_FILE" 2>&1 &
echo "$!" > "$LOCK_FILE"
echo "[$(date)] daemon started (PID $!)" >> "$LOG_FILE"
