"""Unit tests for clipboard backend fallback behavior."""

from __future__ import annotations

import types
from subprocess import CompletedProcess

import pytest

from src.utils import clipboard


def test_copy_to_clipboard_prefers_xclip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(clipboard.shutil, "which", lambda binary: "/usr/bin/xclip" if binary == "xclip" else None)

    def _mock_run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        calls.append(command)
        return CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(clipboard.subprocess, "run", _mock_run)

    assert clipboard.copy_to_clipboard("hello") is True
    assert calls[0] == ["xclip", "-selection", "clipboard"]


def test_copy_to_clipboard_fallback_to_pyperclip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda _: None)

    state: dict[str, str] = {"value": ""}
    fake_pyperclip = types.SimpleNamespace(
        copy=lambda value: state.__setitem__("value", value),
        paste=lambda: state["value"],
    )

    original_import = __import__

    def _mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pyperclip":
            return fake_pyperclip
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    assert clipboard.copy_to_clipboard("fallback") is True
    assert state["value"] == "fallback"


def test_get_from_clipboard_via_xclip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda binary: "/usr/bin/xclip" if binary == "xclip" else None)

    def _mock_run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(args=command, returncode=0, stdout="value-from-xclip", stderr="")

    monkeypatch.setattr(clipboard.subprocess, "run", _mock_run)

    assert clipboard.get_from_clipboard() == "value-from-xclip"


def test_get_from_clipboard_returns_empty_when_all_backends_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda _: None)

    original_import = __import__

    def _mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pyperclip":
            raise ImportError("pyperclip missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    assert clipboard.get_from_clipboard() == ""
