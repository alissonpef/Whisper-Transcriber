#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python"
AUTOSTART_DIR="${HOME}/.config/autostart"
DESKTOP_FILE="${AUTOSTART_DIR}/whisper-daemon.desktop"
ICON_PATH="${SCRIPT_DIR}/assets/icon.png"
RUN_POPUP_SCRIPT="${SCRIPT_DIR}/run_popup.sh"
RUN_DAEMON_SCRIPT="${SCRIPT_DIR}/run_daemon.sh"

is_flatpak_sandbox() {
  [[ -f "/.flatpak-info" || -n "${FLATPAK_ID:-}" ]]
}

delegate_to_host_if_needed() {
  if ! is_flatpak_sandbox; then
    return
  fi

  # Prevent recursion when the installer is relaunched on the host.
  if [[ "${WHISPER_INSTALL_HOST_DELEGATED:-0}" == "1" ]]; then
    return
  fi

  if ! command -v flatpak-spawn >/dev/null 2>&1; then
    echo "Flatpak sandbox detected, but 'flatpak-spawn' is unavailable."
    echo "Run this installer on the host shell and try again."
    exit 1
  fi

  echo "Flatpak sandbox detected. Running installer on host..."
  flatpak-spawn --host env WHISPER_INSTALL_HOST_DELEGATED=1 bash "${SCRIPT_DIR}/install.sh" "$@"
  exit $?
}

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt-get"
    return 0
  fi

  if command -v apt >/dev/null 2>&1; then
    echo "apt"
    return 0
  fi

  return 1
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return 0
  fi

  # In Flatpak-host delegated runs, sudo often has no TTY. Prefer pkexec.
  if [[ "${WHISPER_INSTALL_HOST_DELEGATED:-0}" == "1" ]] && command -v pkexec >/dev/null 2>&1; then
    if pkexec "$@"; then
      return 0
    fi
  fi

  if command -v sudo >/dev/null 2>&1; then
    if sudo -n true >/dev/null 2>&1; then
      if sudo "$@"; then
        return 0
      fi
    fi

    if [[ -t 0 && -t 1 ]]; then
      if sudo "$@"; then
        return 0
      fi
    fi
  fi

  if command -v pkexec >/dev/null 2>&1; then
    if pkexec "$@"; then
      return 0
    fi
  fi

  return 1
}

require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required but was not found."
    exit 1
  fi

  python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required")
PY
}

check_gpu() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "GPU check: nvidia-smi available"
  else
    echo "Warning: nvidia-smi not found. CPU fallback will be used."
  fi
}

install_system_packages() {
  local package_manager

  package_manager="$(detect_package_manager)" || {
    echo "No supported package manager found (expected apt-get or apt). Skipping system package install."
    return 0
  }

  if ! run_as_root env DEBIAN_FRONTEND=noninteractive "${package_manager}" update; then
    echo "Could not elevate privileges to install system packages. Continuing with existing host dependencies."
    return 0
  fi

  if ! run_as_root env DEBIAN_FRONTEND=noninteractive "${package_manager}" install -y \
    python3-pip \
    python3-venv \
    python3-tk \
    portaudio19-dev \
    ffmpeg \
    xclip \
    xsel \
    wmctrl \
    xdotool \
    libportaudio2 \\n    libportaudiocpp0 \\n    build-essential \\n    python3-dev; then
    echo "System package installation failed. Continuing with existing host dependencies."
  fi
}

setup_venv_and_deps() {
  local recreate_venv
  recreate_venv=0

  if [[ ! -d "${VENV_DIR}" ]]; then
    recreate_venv=1
  elif [[ ! -x "${VENV_PY}" ]]; then
    recreate_venv=1
  elif ! "${VENV_PY}" -m pip --version >/dev/null 2>&1; then
    recreate_venv=1
  fi

  if [[ "${recreate_venv}" -eq 1 ]]; then
    rm -rf "${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
  fi

  "${VENV_PY}" -m pip install --upgrade pip
  "${VENV_PY}" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
}

download_model() {
  if [[ "${WHISPER_SKIP_MODEL_DOWNLOAD:-0}" == "1" ]]; then
    echo "Skipping model pre-download (WHISPER_SKIP_MODEL_DOWNLOAD=1)."
    return 0
  fi

  "${VENV_PY}" - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model 'small' ready")
PY

  return 0
}

generate_icon_if_missing() {
  if [[ -f "${ICON_PATH}" ]]; then
    return
  fi

  mkdir -p "$(dirname "${ICON_PATH}")"
  # Minimal PNG fallback icon.
  base64 -d >"${ICON_PATH}" <<'PNG'
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5nK5QAAAAASUVORK5CYII=
PNG
}

create_launchers() {
  cat >"${RUN_POPUP_SCRIPT}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "/.flatpak-info" || -n "${FLATPAK_ID:-}" ]]; then
  exec flatpak-spawn --host bash -lc "cd '${SCRIPT_DIR}' && exec '${SCRIPT_DIR}/.venv/bin/python' -m src.transcriber_popup"
fi

exec "${SCRIPT_DIR}/.venv/bin/python" -m src.transcriber_popup
EOF

  cat >"${RUN_DAEMON_SCRIPT}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "/.flatpak-info" || -n "${FLATPAK_ID:-}" ]]; then
  exec flatpak-spawn --host bash -lc "cd '${SCRIPT_DIR}' && exec '${SCRIPT_DIR}/.venv/bin/python' -m src.hotkey_daemon"
fi

exec "${SCRIPT_DIR}/.venv/bin/python" -m src.hotkey_daemon
EOF

  chmod +x "${RUN_POPUP_SCRIPT}" "${RUN_DAEMON_SCRIPT}"
}

create_autostart_entry() {
  mkdir -p "${AUTOSTART_DIR}"
  cat >"${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Whisper Transcriber Daemon
Comment=Daemon de hotkey para transcricao
Exec=${RUN_DAEMON_SCRIPT}
Path=${SCRIPT_DIR}
Icon=${ICON_PATH}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
}

start_daemon_now() {
  nohup "${VENV_PY}" -m src.hotkey_daemon >/dev/null 2>&1 &
}

main() {
  delegate_to_host_if_needed "$@"
  require_python
  check_gpu
  install_system_packages
  setup_venv_and_deps
  if ! download_model; then
    echo "Model pre-download failed. The app can still download/load on first run."
  fi
  generate_icon_if_missing
  create_launchers
  create_autostart_entry
  start_daemon_now

  echo ""
  echo "✅ Instalado! Pressione Shift+F1 para transcrever."
}

main "$@"
