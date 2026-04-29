from __future__ import annotations


class Theme:
    BG_PRIMARY: str = "#0F1019"
    BG_SECONDARY: str = "#151621"
    BG_HEADER: str = "#1A1D2E"
    BG_FOOTER: str = "#12131E"

    TEXT_PRIMARY: str = "#E8ECF4"
    TEXT_SECONDARY: str = "#8B95A8"
    TEXT_DISABLED: str = "#3E4557"

    COLOR_RECORDING: str = "#F43F5E"
    COLOR_IDLE: str = "#4B5563"
    COLOR_PROCESSING: str = "#F59E0B"
    COLOR_SUCCESS: str = "#34D399"

    BTN_PRIMARY_BG: str = "#6366F1"
    BTN_PRIMARY_FG: str = "#FFFFFF"
    BTN_DANGER_BG: str = "#F43F5E"
    BTN_DANGER_FG: str = "#FFFFFF"
    BTN_GHOST_BG: str = "#1E2030"
    BTN_GHOST_FG: str = "#8B95A8"

    BORDER: str = "#262940"
    SEPARATOR: str = "#1E2030"
    ACCENT: str = "#818CF8"

    DOT_ACTIVE: str = "#F43F5E"
    DOT_PULSE_1: str = "#FB7185"

    WAVEFORM_ACTIVE: str = "#6366F1"
    WAVEFORM_IDLE: str = "#262940"

    FONT_TEXT: tuple[str, int] = ("Inter", 13)
    FONT_STATUS: tuple[str, int, str] = ("Inter", 10, "bold")
    FONT_BTN: tuple[str, int, str] = ("Inter", 10, "bold")
    FONT_LABEL: tuple[str, int] = ("Inter", 9)
    FONT_HEADER: tuple[str, int, str] = ("Inter", 12, "bold")
