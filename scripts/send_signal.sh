#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
POPUP_LOCK="/tmp/whisper_popup.lock"
DAEMON_LOCK="/tmp/whisper_daemon.lock"
LOG_FILE="/tmp/whisper_signal.log"

signal_pid_from_lock() {
  local lock_file="$1"
  if [[ -f "$lock_file" ]]; then
    local pid
    pid="$(cat "$lock_file" 2>/dev/null)" || return 1
    echo "[$(date)] lock=${lock_file} pid=${pid}" >> "$LOG_FILE"
    if kill -SIGUSR1 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

printf '[%s] trigger\n' "$(date)" >> "$LOG_FILE"

if signal_pid_from_lock "$POPUP_LOCK"; then
  printf '[%s] popup signaled\n' "$(date)" >> "$LOG_FILE"
  exit 0
fi

if signal_pid_from_lock "$DAEMON_LOCK"; then
  printf '[%s] daemon signaled\n' "$(date)" >> "$LOG_FILE"
  exit 0
fi

printf '[%s] launching popup\n' "$(date)" >> "$LOG_FILE"
exec "${PROJECT_DIR}/scripts/run_popup.sh" --record
