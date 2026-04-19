#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_FILE="${HOME}/.config/autostart/whisper-daemon.desktop"
LOGS_DIR="${HOME}/.local/share/whisper-transcriber"
MODEL_CACHE_DIR_HF="${HOME}/.cache/huggingface/hub"
MODEL_CACHE_DIR_FW="${HOME}/.cache/faster-whisper"

remove_autostart() {
  rm -f "${AUTOSTART_FILE}"
  echo "Autostart entry removed."
}

stop_daemon() {
  pkill -f "python -m src.hotkey_daemon" || true
  rm -f /tmp/whisper_daemon.lock /tmp/whisper_popup.lock
  echo "Daemon stopped (if it was running)."
}

confirm() {
  local prompt="$1"
  read -r -p "${prompt} [y/N]: " answer
  [[ "${answer}" =~ ^[Yy]$ ]]
}

remove_logs() {
  if [[ -d "${LOGS_DIR}" ]]; then
    rm -rf "${LOGS_DIR}"
    echo "Logs removed."
  fi
}

remove_models() {
  rm -rf "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-small"
  rm -rf "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-medium"
  rm -rf "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-tiny"
  rm -rf "${MODEL_CACHE_DIR_FW}/small" "${MODEL_CACHE_DIR_FW}/medium" "${MODEL_CACHE_DIR_FW}/tiny"
  echo "Known model cache directories removed."
}

main() {
  remove_autostart
  stop_daemon

  if confirm "Remove logs at ${LOGS_DIR}?"; then
    remove_logs
  else
    echo "Logs kept."
  fi

  if confirm "Remove Whisper model caches?"; then
    remove_models
  else
    echo "Model caches kept."
  fi

  echo "Uninstall complete."
}

main "$@"
