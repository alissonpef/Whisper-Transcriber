from __future__ import annotations

import tkinter as tk

from src.ui.theme import Theme


class StatusDotAnimator:
    def __init__(self, root: tk.Tk, canvas: tk.Canvas, dot_id: int) -> None:
        self._root = root
        self._canvas = canvas
        self._dot_id = dot_id
        self._state: str = "IDLE"
        self._pulse: bool = False
        self._job: str | None = None

    def set_state(self, state: str) -> None:
        self._state = state
        self._render()

    def stop(self) -> None:
        if self._job is not None:
            self._root.after_cancel(self._job)
            self._job = None

    def _render(self) -> None:
        self.stop()
        if self._state == "RECORDING":
            self._pulse = not self._pulse
            if self._pulse:
                self._canvas.coords(self._dot_id, 2, 2, 14, 14)
                self._canvas.itemconfig(self._dot_id, fill=Theme.DOT_PULSE_1)
            else:
                self._canvas.coords(self._dot_id, 4, 4, 12, 12)
                self._canvas.itemconfig(self._dot_id, fill=Theme.DOT_ACTIVE)
            self._job = self._root.after(400, self._render)
            return

        if self._state in {"LOADING", "PROCESSING"}:
            self._pulse = not self._pulse
            color = Theme.COLOR_PROCESSING if self._pulse else Theme.COLOR_IDLE
            self._canvas.coords(self._dot_id, 4, 4, 12, 12)
            self._canvas.itemconfig(self._dot_id, fill=color)
            self._job = self._root.after(200, self._render)
            return

        self._canvas.coords(self._dot_id, 4, 4, 12, 12)
        self._canvas.itemconfig(self._dot_id, fill=Theme.COLOR_IDLE)


def fade_in(root: tk.Tk, alpha: float = 0.0) -> None:
    if alpha >= 1.0:
        root.attributes("-alpha", 1.0)
        return
    root.attributes("-alpha", alpha)
    root.after(10, fade_in, root, alpha + 0.07)
