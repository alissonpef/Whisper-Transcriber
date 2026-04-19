"""Hardware and runtime availability checks for Whisper transcription."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)

HF_CACHE_DIR: Path = Path.home() / ".cache" / "huggingface" / "hub"
FW_CACHE_DIR: Path = Path.home() / ".cache" / "faster-whisper"


def check_gpu() -> dict[str, Any]:
    """Check NVIDIA GPU availability and estimate VRAM in GB."""
    command: list[str] = [
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return {"available": False, "name": "", "vram_gb": 0.0}

    if result.returncode != 0 or not result.stdout.strip():
        return {"available": False, "name": "", "vram_gb": 0.0}

    first_line: str = result.stdout.strip().splitlines()[0]
    parts: list[str] = [part.strip() for part in first_line.split(",")]
    if len(parts) < 2:
        return {"available": False, "name": "", "vram_gb": 0.0}

    name: str = parts[0]
    try:
        vram_mb: float = float(parts[1])
    except ValueError:
        vram_mb = 0.0

    return {
        "available": bool(name),
        "name": name,
        "vram_gb": round(vram_mb / 1024.0, 2),
    }


def check_microphone() -> dict[str, Any]:
    """Check microphone devices from sounddevice, if available."""
    try:
        import sounddevice as sd  # type: ignore[import-untyped]
    except Exception:
        logger.warning("sounddevice not available for microphone discovery")
        return {"available": False, "devices": [], "default": ""}

    try:
        devices_raw: list[dict[str, Any]] = list(sd.query_devices())
        default_input: Any = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device

        input_devices: list[dict[str, Any]] = [
            d for d in devices_raw if int(d.get("max_input_channels", 0)) > 0
        ]
        names: list[str] = [str(d.get("name", "")).strip() for d in input_devices if str(d.get("name", "")).strip()]

        default_name: str = ""
        if isinstance(default_input, int) and 0 <= default_input < len(devices_raw):
            default_name = str(devices_raw[default_input].get("name", "")).strip()

        return {
            "available": len(names) > 0,
            "devices": names,
            "default": default_name,
        }
    except Exception:
        logger.exception("Failed to inspect microphone devices")
        return {"available": False, "devices": [], "default": ""}


def check_model_cached(size: str) -> bool:
    """Return True when a Whisper model cache directory is already present."""
    normalized: str = size.strip().lower()
    candidates: list[Path] = [
        HF_CACHE_DIR / f"models--Systran--faster-whisper-{normalized}",
        HF_CACHE_DIR / f"models--openai--whisper-{normalized}",
        FW_CACHE_DIR / normalized,
        FW_CACHE_DIR / f"faster-whisper-{normalized}",
        FW_CACHE_DIR / f"Systran-faster-whisper-{normalized}",
    ]
    return any(path.exists() for path in candidates)


def check_all() -> dict[str, Any]:
    """Return a combined environment report."""
    return {
        "gpu": check_gpu(),
        "microphone": check_microphone(),
        "model_cached": check_model_cached("small"),
    }
