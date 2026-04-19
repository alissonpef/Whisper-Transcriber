"""Unit tests for device and cache checks."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from src.utils import device_check


@pytest.mark.parametrize(
    "stdout, expected_name, expected_vram",
    [
        ("NVIDIA GeForce RTX 4050, 6144\n", "NVIDIA GeForce RTX 4050", 6.0),
        ("RTX, 2048\n", "RTX", 2.0),
    ],
)
def test_check_gpu_parses_nvidia_smi(monkeypatch: pytest.MonkeyPatch, stdout: str, expected_name: str, expected_vram: float) -> None:
    def _mock_run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(device_check.subprocess, "run", _mock_run)

    result = device_check.check_gpu()
    assert result["available"] is True
    assert result["name"] == expected_name
    assert result["vram_gb"] == expected_vram


def test_check_gpu_when_nvidia_smi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        raise FileNotFoundError

    monkeypatch.setattr(device_check.subprocess, "run", _mock_run)

    result = device_check.check_gpu()
    assert result == {"available": False, "name": "", "vram_gb": 0.0}


def test_check_microphone_without_sounddevice(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = __import__

    def _mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "sounddevice":
            raise ImportError("no module named sounddevice")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)
    result = device_check.check_microphone()
    assert result["available"] is False
    assert result["devices"] == []


def test_check_model_cached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hf_dir = tmp_path / "huggingface" / "hub"
    fw_dir = tmp_path / "faster-whisper"
    hf_model = hf_dir / "models--Systran--faster-whisper-small"
    hf_model.mkdir(parents=True)

    monkeypatch.setattr(device_check, "HF_CACHE_DIR", hf_dir)
    monkeypatch.setattr(device_check, "FW_CACHE_DIR", fw_dir)

    assert device_check.check_model_cached("small") is True
    assert device_check.check_model_cached("medium") is False


def test_check_all_returns_expected_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device_check, "check_gpu", lambda: {"available": False, "name": "", "vram_gb": 0.0})
    monkeypatch.setattr(device_check, "check_microphone", lambda: {"available": False, "devices": [], "default": ""})
    monkeypatch.setattr(device_check, "check_model_cached", lambda size: size == "small")

    report = device_check.check_all()
    assert "gpu" in report
    assert "microphone" in report
    assert "model_cached" in report
    assert report["model_cached"] is True
