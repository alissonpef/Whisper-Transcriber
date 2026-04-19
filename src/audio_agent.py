"""Audio capture agent backed by sounddevice InputStream."""

from __future__ import annotations

import queue
import threading
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.config import AudioConfig
from src.logger import get_logger

try:
    import sounddevice as sd  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - exercised by runtime envs without sounddevice
    sd = None


logger = get_logger(__name__)


class AudioAgent:
    """Capture microphone chunks and enqueue them for transcription."""

    def __init__(self, queue_obj: queue.Queue[NDArray[np.float32]], config: AudioConfig) -> None:
        self._queue: queue.Queue[NDArray[np.float32]] = queue_obj
        self._config: AudioConfig = config
        self._stream: Any | None = None
        self._state_recording: bool = False
        self._state_lock = threading.Lock()

    def start(self) -> None:
        """Start audio capture stream."""
        with self._state_lock:
            if self._state_recording:
                return
            if sd is None:
                raise RuntimeError("sounddevice is not available")

            self._stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype=self._config.dtype,
                blocksize=self._config.blocksize,
                callback=self._callback,
            )
            self._stream.start()
            self._state_recording = True
            logger.info("Audio stream started")

    def stop(self) -> None:
        """Stop audio stream and drain pending chunks."""
        with self._state_lock:
            self._state_recording = False
            stream = self._stream
            self._stream = None

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                logger.exception("Failed to stop audio stream cleanly")

        self._drain_queue()
        logger.info("Audio stream stopped")

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _callback(
        self,
        indata: NDArray[np.float32],
        frames: int,
        time: Any,
        status: Any,
    ) -> None:
        """Sounddevice callback: copy and enqueue quickly, never block."""
        if status:
            logger.warning("Audio callback status: %s", status)

        if not self._state_recording:
            return

        try:
            self._queue.put_nowait(indata.copy())
        except queue.Full:
            logger.warning("Audio queue full; dropping chunk of %s frames", frames)
