#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTOSTART_FILE="${HOME}/.config/autostart/whisper-daemon.desktop"
LOGS_DIR="${HOME}/.local/share/whisper-transcriber"
MODEL_CACHE_DIR_HF="${HOME}/.cache/huggingface/hub"
MODEL_CACHE_DIR_FW="${HOME}/.cache/faster-whisper"

remove_autostart() {
  rm -f "$AUTOSTART_FILE"
}

stop_daemon() {
  pkill -f "python.*src.hotkey_daemon" || true
  pkill -f "python.*src.transcriber_popup" || true
  rm -f /tmp/whisper_daemon.lock /tmp/whisper_popup.lock
}

remove_gnome_shortcut() {
  if ! command -v gsettings >/dev/null 2>&1; then
    return 0
  fi

  local schema="org.gnome.settings-daemon.plugins.media-keys"
  local custom_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper-transcriber/"
  local current
  current="$(gsettings get "${schema}" custom-keybindings 2>/dev/null || echo "@as []")"

  if [[ "${current}" == *"whisper-transcriber"* ]]; then
    local updated
    updated="$(echo "${current}" | sed "s|, '${custom_path}'||g; s|'${custom_path}', ||g; s|'${custom_path}'||g")"
    gsettings set "${schema}" custom-keybindings "${updated}" 2>/dev/null || true
    local kb_schema="${schema}.custom-keybinding:${custom_path}"
    gsettings reset "${kb_schema}" name 2>/dev/null || true
    gsettings reset "${kb_schema}" command 2>/dev/null || true
    gsettings reset "${kb_schema}" binding 2>/dev/null || true
  fi
}

confirm() {
  local prompt="$1"
  read -r -p "${prompt} [y/N]: " answer
  [[ "${answer}" =~ ^[Yy]$ ]]
}

remove_logs() {
  rm -rf "$LOGS_DIR" /tmp/whisper-transcriber.log /tmp/whisper_signal.log
}

remove_models() {
  rm -rf \
    "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-small" \
    "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-medium" \
    "${MODEL_CACHE_DIR_HF}/models--Systran--faster-whisper-tiny" \
    "${MODEL_CACHE_DIR_FW}/small" \
    "${MODEL_CACHE_DIR_FW}/medium" \
    "${MODEL_CACHE_DIR_FW}/tiny"
}

main() {
  remove_autostart
  stop_daemon
  remove_gnome_shortcut

  if confirm "Remove logs at ${LOGS_DIR}?"; then
    remove_logs
  fi

  if confirm "Remove Whisper model caches?"; then
    remove_models
  fi
}

main "$@"
