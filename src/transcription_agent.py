"""Transcription worker that consumes audio chunks and emits text results."""

from __future__ import annotations

import copy
import queue
import threading
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from src.config import AUDIO, MODEL, ModelConfig
from src.logger import get_logger

logger = get_logger(__name__)


class TranscriptionAgent:
    """Background worker that transcribes buffered chunks with Whisper."""

    def __init__(
        self,
        audio_queue: queue.Queue[NDArray[np.float32]],
        on_result: Callable[[str], None],
        config: ModelConfig,
        model_override: Any | None = None,
    ) -> None:
        self._audio_queue: queue.Queue[NDArray[np.float32]] = audio_queue
        self._on_result: Callable[[str], None] = on_result
        self._config: ModelConfig = copy.copy(config)
        self._model: Any | None = model_override
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._fallback_lock = threading.Lock()

        self._active_device: str = self._config.device
        self._active_compute_type: str = self._config.compute_type

    def load_model(self, on_progress: Callable[[str], None] | None = None) -> None:
        """Load Whisper model once, trying CPU fallback when configured."""
        if self._model is not None:
            if on_progress:
                on_progress("model-ready")
            return

        if on_progress:
            on_progress("loading-model")

        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        try:
            self._model = WhisperModel(
                self._config.size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
            self._active_device = self._config.device
            self._active_compute_type = self._config.compute_type
        except Exception:
            if not self._config.cpu_fallback or self._config.device == "cpu":
                logger.exception("Failed to load Whisper model")
                raise

            logger.warning("CUDA load failed; falling back to CPU int8")
            self._model = WhisperModel(
                self._config.size,
                device="cpu",
                compute_type="int8",
            )
            self._active_device = "cpu"
            self._active_compute_type = "int8"

        if on_progress:
            on_progress("model-ready")

    def start(self) -> None:
        """Start transcription worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self.load_model()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()
        logger.info("Transcription agent started")

    def stop(self) -> None:
        """Stop worker thread and release pending queue items quickly."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Transcription agent stopped")

    def get_runtime_details(self) -> tuple[str, str, str]:
        """Return current model, device, and compute type used by the worker."""
        return self._config.size, self._active_device, self._active_compute_type

    def _transcribe_loop(self) -> None:
        buffer: list[NDArray[np.float32]] = []
        buffered_frames: int = 0
        required_frames: int = int(AUDIO.sample_rate * AUDIO.chunk_secs)

        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.2)
                buffer.append(chunk)
                buffered_frames += int(chunk.shape[0])

                if buffered_frames < required_frames:
                    continue

                merged: NDArray[np.float32] = np.concatenate(buffer, axis=0).reshape(-1)
                buffer = []
                buffered_frames = 0

                self._run_transcription(merged)
            except queue.Empty:
                continue
            except Exception:
                logger.exception("Unexpected transcription loop error")

    def _run_transcription(self, audio: NDArray[np.float32]) -> None:
        if self._model is None:
            return

        try:
            text = self._transcribe_text(audio)
            if text:
                self._on_result(text)
        except Exception as exc:
            if self._should_fallback_runtime(exc) and self._fallback_to_cpu():
                try:
                    text = self._transcribe_text(audio)
                    if text:
                        self._on_result(text)
                    return
                except Exception:
                    logger.exception("CPU fallback retry failed")
            logger.exception("Model transcribe failed; continuing loop")

    def _transcribe_text(self, audio: NDArray[np.float32]) -> str:
        if self._model is None:
            return ""

        segments, _ = self._model.transcribe(
            audio,
            language=self._config.language,
            beam_size=self._config.beam_size,
        )
        return " ".join(
            str(getattr(segment, "text", "")).strip() for segment in segments
        ).strip()

    def _should_fallback_runtime(self, exc: Exception) -> bool:
        if not self._config.cpu_fallback or self._active_device == "cpu":
            return False

        message = str(exc).lower()
        cuda_markers = (
            "cublas",
            "cudnn",
            "libcuda",
            "cuda",
            "cannot be loaded",
            "no cuda",
        )
        return any(marker in message for marker in cuda_markers)

    def _fallback_to_cpu(self) -> bool:
        with self._fallback_lock:
            if self._active_device == "cpu":
                return True

            try:
                from faster_whisper import WhisperModel  # type: ignore[import-untyped]

                logger.warning("Runtime CUDA failure; switching to CPU int8")
                self._model = WhisperModel(
                    self._config.size,
                    device="cpu",
                    compute_type="int8",
                )
                self._active_device = "cpu"
                self._active_compute_type = "int8"
                return True
            except Exception:
                logger.exception("Failed to initialize CPU fallback model")
                return False
