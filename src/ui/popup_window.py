"""Main popup window that orchestrates UI, audio capture, and transcription."""

from __future__ import annotations

import queue
import signal
import threading
import tkinter as tk
from typing import Any

from src.audio_agent import AudioAgent
from src.config import AUDIO, MODEL, UI
from src.logger import get_logger
from src.transcription_agent import TranscriptionAgent
from src.ui.behaviors import StatusDotAnimator, fade_in
from src.ui.components import ActionButton, LoadingSpinner, StatusBar, TranscriptArea
from src.ui.theme import Theme
from src.utils.clipboard import copy_to_clipboard
from src.utils.lockfile import acquire, release

logger = get_logger(__name__)


class PopupWindow:
    """Frameless popup UI for real-time speech transcription."""

    def __init__(self, auto_start_recording: bool = False) -> None:
        if not acquire():
            raise RuntimeError("Popup already running")

        self._state: str = "LOADING"
        self._closing: bool = False
        self._recording: bool = False
        self._auto_start_recording: bool = bool(auto_start_recording or UI.auto_start_recording)
        self._model_ready: bool = False
        self._drag_x: int = 0
        self._drag_y: int = 0
        self._frameless: bool = False
        self._restore_pending: bool = False

        self.root = tk.Tk()
        self.root.title("Transcritor Whisper")
        self.root.configure(bg=Theme.BG_PRIMARY)
        self.root.minsize(UI.min_width, UI.min_height)

        if UI.always_on_top:
            self.root.attributes("-topmost", True)

        self._set_geometry()

        # Frameless window with custom draggable header.
        self.root.overrideredirect(True)
        self._frameless = True
        self.root.attributes("-alpha", 0.0)

        self.audio_queue: queue.Queue[Any] = queue.Queue(maxsize=AUDIO.queue_maxsize)
        self.audio_agent = AudioAgent(self.audio_queue, AUDIO)
        self.transcription_agent = TranscriptionAgent(
            audio_queue=self.audio_queue,
            on_result=lambda text: self.root.after(0, self._insert_text, text),
            config=MODEL,
        )

        self._build_layout()
        self._bind_shortcuts()
        self._register_hotkey_signal()
        self._set_visual_state("LOADING")

        self.root.after(0, fade_in, self.root, 0.0)
        self.root.after(10, self._load_model_async)

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            self._on_close()

    def _set_geometry(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = int((screen_w - UI.width) / 2)
        y = int((screen_h - UI.height) / 2)
        self.root.geometry(f"{UI.width}x{UI.height}+{x}+{y}")

    def _build_layout(self) -> None:
        self.header = tk.Frame(self.root, bg=Theme.BG_HEADER, height=44)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        self.dot_canvas = tk.Canvas(
            self.header,
            width=16,
            height=16,
            bg=Theme.BG_HEADER,
            highlightthickness=0,
        )
        self.dot_canvas.pack(side=tk.LEFT, padx=(12, 6))
        self.dot_id = self.dot_canvas.create_oval(4, 4, 12, 12, fill=Theme.COLOR_IDLE, outline="")
        self.dot_animator = StatusDotAnimator(self.root, self.dot_canvas, self.dot_id)

        self.title_label = tk.Label(
            self.header,
            text="Transcritor Whisper",
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_HEADER,
        )
        self.title_label.pack(side=tk.LEFT)

        self.close_btn = tk.Button(
            self.header,
            text="X",
            command=self._on_close,
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.BTN_DANGER_BG,
            activeforeground=Theme.BTN_DANGER_FG,
            relief=tk.FLAT,
            bd=0,
            width=3,
            highlightthickness=0,
            cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(0, 8))

        self.min_btn = tk.Button(
            self.header,
            text="-",
            command=self._on_minimize,
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_PRIMARY,
            activebackground=Theme.BORDER,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            bd=0,
            width=3,
            highlightthickness=0,
            cursor="hand2",
        )
        self.min_btn.pack(side=tk.RIGHT, padx=(0, 4))

        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X)
        self._update_status_meta()

        self.footer = tk.Frame(self.root, bg=Theme.BG_FOOTER, height=56)
        self.footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer.pack_propagate(False)

        self.transcript = TranscriptArea(self.root)
        self.transcript.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toggle_btn = ActionButton(self.footer, text="Start", command=self._on_toggle_recording, variant="primary", width=12)
        self.toggle_btn.pack(side=tk.LEFT, padx=(12, 8), pady=10)
        self.toggle_btn.configure(state=tk.DISABLED)

        self.copy_all_btn = ActionButton(self.footer, text="Copy", command=self._on_copy_all, variant="ghost", width=10)
        self.copy_all_btn.pack(side=tk.LEFT, padx=4, pady=10)

        self.clear_btn = ActionButton(self.footer, text="Clear", command=self._on_clear, variant="ghost", width=8)
        self.clear_btn.pack(side=tk.LEFT, padx=4, pady=10)

        self.loading = LoadingSpinner(self.root)

        for widget in (self.header, self.title_label, self.dot_canvas):
            widget.bind("<ButtonPress-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Escape>", lambda _event: self._on_close())
        self.root.bind("<Control-Shift-C>", lambda _event: self._on_copy_all())
        self.root.bind("<Control-Shift-L>", lambda _event: self._on_clear())
        self.root.bind("<Control-Shift-space>", lambda _event: self._on_toggle_recording())
        self.root.bind("<Shift-F1>", lambda _event: self._on_toggle_recording())
        self.root.bind("<Map>", self._on_window_map)

    def _register_hotkey_signal(self) -> None:
        sigusr1 = getattr(signal, "SIGUSR1", None)
        if sigusr1 is None:
            return

        try:
            signal.signal(sigusr1, self._on_hotkey_signal)
        except (ValueError, OSError):
            logger.exception("Unable to register hotkey signal handler")

    def _on_hotkey_signal(self, _signum: int, _frame: Any) -> None:
        if self._closing:
            return
        self.root.after(0, self._start_recording_from_hotkey)

    def _start_recording_from_hotkey(self) -> None:
        if self._closing:
            return

        self._show_window()
        if not self._model_ready:
            self._auto_start_recording = True
            return

        self._start_recording()

    def _show_window(self) -> None:
        try:
            deiconify = getattr(self.root, "deiconify", None)
            if callable(deiconify):
                deiconify()

            lift = getattr(self.root, "lift", None)
            if callable(lift):
                lift()

            focus_force = getattr(self.root, "focus_force", None)
            if callable(focus_force):
                focus_force()

            self.root.after(10, self._restore_frameless)
        except tk.TclError:
            logger.exception("Failed to raise popup window")

    def _load_model_async(self) -> None:
        self.loading.show("Whisper small · CUDA · PT-BR")

        def worker() -> None:
            try:
                self.transcription_agent.load_model(
                    on_progress=lambda message: self.root.after(0, self.loading.set_message, message)
                )
                self.root.after(0, self._on_model_ready)
            except Exception as exc:
                logger.exception("Model loading failed")
                self.root.after(0, self._on_model_failed, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_model_ready(self) -> None:
        self._model_ready = True
        self._update_status_meta()
        self.loading.hide()
        self.transcription_agent.start()
        self.toggle_btn.configure(state=tk.NORMAL)
        self._set_visual_state("IDLE")
        if self._auto_start_recording:
            self._start_recording()

    def _update_status_meta(self) -> None:
        model_size = MODEL.size
        device = MODEL.device
        compute_type = MODEL.compute_type

        details_getter = getattr(self.transcription_agent, "get_runtime_details", None)
        if callable(details_getter):
            model_size, device, compute_type = details_getter()

        self.status_bar.set_meta(f"modelo: {model_size} · PT-BR · {device.upper()} ({compute_type})")

    def _on_model_failed(self, reason: str) -> None:
        self.loading.hide()
        self._set_visual_state("IDLE")
        self.status_bar.set_state(f"Erro ao carregar modelo: {reason}", Theme.COLOR_RECORDING)

    def _on_minimize(self) -> None:
        if self._closing:
            return

        try:
            self._restore_pending = True
            if self._frameless:
                self.root.overrideredirect(False)
                self._frameless = False

            if UI.always_on_top:
                self.root.attributes("-topmost", False)

            update_idletasks = getattr(self.root, "update_idletasks", None)
            if callable(update_idletasks):
                update_idletasks()

            self.root.after(50, self.root.iconify)
        except tk.TclError:
            logger.exception("Failed to minimize popup window")

    def _on_window_map(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._restore_pending:
            return

        state_getter = getattr(self.root, "state", None)
        if callable(state_getter):
            try:
                if state_getter() != "normal":
                    return
            except tk.TclError:
                return

        self.root.after(10, self._restore_frameless)

    def _restore_frameless(self) -> None:
        if self._closing:
            return

        if self._frameless:
            self._restore_pending = False
            if UI.always_on_top:
                self.root.attributes("-topmost", True)
            return

        try:
            self.root.overrideredirect(True)
            self._frameless = True
            self._restore_pending = False
            if UI.always_on_top:
                self.root.attributes("-topmost", True)
        except tk.TclError:
            logger.exception("Failed to restore frameless popup style")

    def _on_drag_start(self) -> None:
        pass

