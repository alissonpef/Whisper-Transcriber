"""Reusable tkinter UI components for the transcriber popup."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Literal

from src.ui.theme import Theme

ButtonVariant = Literal["primary", "danger", "ghost"]


def _adjust_color(hex_color: str, amount: int) -> str:
    """Lighten or darken a #RRGGBB color by an integer amount."""
    color = hex_color[:7]
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)

    red = max(0, min(255, red + amount))
    green = max(0, min(255, green + amount))
    blue = max(0, min(255, blue + amount))
    return f"#{red:02X}{green:02X}{blue:02X}"


class StatusBar(tk.Frame):
    """Top status row with state text and right-side metadata."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=Theme.BG_PRIMARY, height=28, highlightthickness=1)
        self.configure(highlightbackground=Theme.BORDER)
        self.pack_propagate(False)

        self._state_label = tk.Label(
            self,
            text="⏸ Pronto para gravar",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_STATUS,
            anchor="w",
        )
        self._meta_label = tk.Label(
            self,
            text="modelo: small · PT-BR · CUDA",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED,
            font=Theme.FONT_LABEL,
            anchor="e",
        )

        self._state_label.pack(side=tk.LEFT, padx=12)
        self._meta_label.pack(side=tk.RIGHT, padx=12)

    def set_state(self, text: str, color: str) -> None:
        self._state_label.configure(text=text, fg=color)

    def set_meta(self, text: str) -> None:
        self._meta_label.configure(text=text)


class TranscriptArea(tk.Frame):
    """Editable transcript text area with styled vertical scrollbar."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=Theme.BG_SECONDARY)

        style = ttk.Style(self)
        style.configure(
            "Transcript.Vertical.TScrollbar",
            background=Theme.BORDER,
            troughcolor=Theme.BG_SECONDARY,
            arrowcolor=Theme.BORDER,
            bordercolor=Theme.BG_SECONDARY,
            darkcolor=Theme.BORDER,
            lightcolor=Theme.BORDER,
            gripcount=0,
            width=6,
        )

        self.text_widget = tk.Text(
            self,
            wrap="word",
            undo=True,
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            bd=0,
            font=Theme.FONT_TEXT,
            padx=12,
            pady=12,
            spacing1=2,
            spacing3=2,
        )

        self.scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.text_widget.yview,
            style="Transcript.Vertical.TScrollbar",
        )
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)

        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def append(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            return

        current = self.text_widget.get("1.0", tk.END).strip()
        prefix = " " if current else ""
        self.text_widget.insert(tk.END, f"{prefix}{clean}")
        self.text_widget.see(tk.END)

    def clear(self) -> None:
        self.text_widget.delete("1.0", tk.END)

    def get_text(self) -> str:
        return self.text_widget.get("1.0", tk.END).strip()


class ActionButton(tk.Button):
    """Themed button with visual variants and hover behavior."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        variant: ButtonVariant,
        width: int,
    ) -> None:
        self._variant = variant
        self._base_bg, fg = self._resolve_palette(variant)

        super().__init__(
            parent,
            text=text,
            command=command,
            width=width,
            bg=self._base_bg,
            fg=fg,
            activebackground=_adjust_color(self._base_bg, 14),
            activeforeground=fg,
            font=Theme.FONT_BTN,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            highlightthickness=0,
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    @staticmethod
    def _resolve_palette(variant: ButtonVariant) -> tuple[str, str]:
        if variant == "primary":
            return Theme.BTN_PRIMARY_BG, Theme.BTN_PRIMARY_FG
        if variant == "danger":
            return Theme.BTN_DANGER_BG, Theme.BTN_DANGER_FG
        return Theme.BTN_GHOST_BG, Theme.BTN_GHOST_FG

    def set_variant(self, variant: ButtonVariant) -> None:
        self._variant = variant
        self._base_bg, fg = self._resolve_palette(variant)
        self.configure(
            bg=self._base_bg,
            fg=fg,
            activebackground=_adjust_color(self._base_bg, 14),
            activeforeground=fg,
        )

    def _on_enter(self, _event: tk.Event[tk.Misc]) -> None:
        self.configure(bg=_adjust_color(self._base_bg, 14))

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        self.configure(bg=self._base_bg)


class LoadingSpinner(tk.Frame):
    """Overlay loading panel with indeterminate progress and animated dots."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=Theme.BG_PRIMARY)
        self._running: bool = False
        self._dot_index: int = 0
        self._message_base: str = "Whisper small · CUDA · PT-BR"

        self._title = tk.Label(
            self,
            text="⚡ Carregando modelo",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_HEADER,
        )
        self._title.pack(pady=(120, 10))

        self._progress = ttk.Progressbar(self, mode="indeterminate", length=220)
        self._progress.pack(pady=10)

        self._message = tk.Label(
            self,
            text=self._message_base,
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_LABEL,
        )
        self._message.pack(pady=(8, 0))

    def show(self, message: str | None = None) -> None:
        if message is not None:
            self._message_base = message
        self.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self._running = True
        self._progress.start(12)
        self._animate_dots()

    def hide(self) -> None:
        self._running = False
        self._progress.stop()
        self.place_forget()

    def set_message(self, message: str) -> None:
        self._message_base = message
        self._message.configure(text=message)

    def _animate_dots(self) -> None:
        if not self._running:
            return
        dots = "." * ((self._dot_index % 3) + 1)
        self._message.configure(text=f"{self._message_base}{dots}")
        self._dot_index += 1
        self.after(350, self._animate_dots)
