"""UI component tests for tkinter widgets."""

from __future__ import annotations

import os

import pytest

tk = pytest.importorskip("tkinter")

from src.ui.components import ActionButton, LoadingSpinner, StatusBar, TranscriptArea


HAS_DISPLAY = bool(os.environ.get("DISPLAY"))


@pytest.mark.skipif(not HAS_DISPLAY, reason="Tkinter display not available")
def test_transcript_area_append() -> None:
    root = tk.Tk()
    root.withdraw()
    area = TranscriptArea(root)
    area.append("ola")
    area.append("mundo")

    assert area.get_text() == "ola mundo"
    root.destroy()


@pytest.mark.skipif(not HAS_DISPLAY, reason="Tkinter display not available")
def test_statusbar_state_update() -> None:
    root = tk.Tk()
    root.withdraw()
    bar = StatusBar(root)
    bar.set_state("🔴 Gravando...", "#EF4444")
    bar.set_meta("modelo: small · PT-BR · CPU")

    assert bar.winfo_exists() == 1
    root.destroy()


@pytest.mark.skipif(not HAS_DISPLAY, reason="Tkinter display not available")
def test_action_button_variant_switch() -> None:
    root = tk.Tk()
    root.withdraw()
    clicked = {"value": False}

    btn = ActionButton(root, text="Teste", command=lambda: clicked.__setitem__("value", True), variant="primary", width=10)
    btn.invoke()
    btn.set_variant("danger")

    assert clicked["value"] is True
    root.destroy()


@pytest.mark.skipif(not HAS_DISPLAY, reason="Tkinter display not available")
def test_loading_spinner_show_hide() -> None:
    root = tk.Tk()
    root.withdraw()

    spinner = LoadingSpinner(root)
    spinner.show("Carregando")
    root.update_idletasks()
    assert spinner.winfo_manager() == "place"

    spinner.hide()
    root.update_idletasks()
    assert spinner.winfo_manager() == ""
    root.destroy()
