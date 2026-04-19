"""Centralized visual theme constants for the tkinter popup UI."""

from __future__ import annotations


class Theme:
    """UI colors and typography constants from ui_spec.md."""

    BG_PRIMARY: str = "#1A1B2E"
    BG_SECONDARY: str = "#16213E"
    BG_HEADER: str = "#0F3460"
    BG_FOOTER: str = "#1A1B2E"

    TEXT_PRIMARY: str = "#E2E8F0"
    TEXT_SECONDARY: str = "#94A3B8"
    TEXT_DISABLED: str = "#475569"

    COLOR_RECORDING: str = "#EF4444"
    COLOR_IDLE: str = "#64748B"
    COLOR_PROCESSING: str = "#F59E0B"
    COLOR_SUCCESS: str = "#10B981"

    BTN_PRIMARY_BG: str = "#3B82F6"
    BTN_PRIMARY_FG: str = "#FFFFFF"
    BTN_DANGER_BG: str = "#EF4444"
    BTN_DANGER_FG: str = "#FFFFFF"
    BTN_GHOST_BG: str = "#1E293B"
    BTN_GHOST_FG: str = "#94A3B8"
    BTN_HOVER_ALPHA: str = "#CBD5E1"

    BORDER: str = "#334155"
    SEPARATOR: str = "#1E293B"

    DOT_ACTIVE: str = "#EF4444"
    DOT_PULSE_1: str = "#F87171"
    DOT_PULSE_2: str = "#FCA5A5"

    FONT_FAMILY: str = "Inter"
    FONT_FALLBACK: list[str] = ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"]

    FONT_TEXT: tuple[str, int] = ("Inter", 13)
    FONT_STATUS: tuple[str, int, str] = ("Inter", 10, "bold")
    FONT_BTN: tuple[str, int, str] = ("Inter", 10, "bold")
    FONT_LABEL: tuple[str, int] = ("Inter", 9)
    FONT_HEADER: tuple[str, int, str] = ("Inter", 12, "bold")
