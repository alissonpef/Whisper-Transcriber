"""Unit tests for centralized configuration objects."""

from __future__ import annotations


def test_config_imports() -> None:
    from src.config import AUDIO, HOTKEY, MODEL, UI

    assert AUDIO is not None
    assert MODEL is not None
    assert HOTKEY is not None
    assert UI is not None


def test_audio_config_values() -> None:
    from src.config import AUDIO

    assert AUDIO.sample_rate == 16000
    assert AUDIO.channels == 1
    assert AUDIO.dtype == "float32"
    assert AUDIO.chunk_secs > 0


def test_model_config_device_valid() -> None:
    from src.config import MODEL

    assert MODEL.device in ("cuda", "cpu")
    assert MODEL.size in ("tiny", "base", "small", "medium", "large-v3")


def test_hotkey_default_combination() -> None:
    from src.config import HOTKEY

    assert HOTKEY.combination == "<shift>+<f1>"


def test_ui_config_dimensions() -> None:
    from src.config import UI

    assert UI.width >= UI.min_width
    assert UI.height >= UI.min_height
