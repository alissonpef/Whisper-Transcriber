"""Unit tests for AudioAgent behavior."""

from __future__ import annotations

import queue
from typing import Any

import numpy as np
import pytest

from src.audio_agent import AudioAgent
from src.config import AUDIO


@pytest.fixture
def audio_queue() -> queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]:
    return queue.Queue(maxsize=100)


def test_audio_agent_instantiation(audio_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]) -> None:
    agent = AudioAgent(audio_queue, AUDIO)
    assert agent is not None


def test_callback_puts_data_in_queue(audio_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]) -> None:
    agent = AudioAgent(audio_queue, AUDIO)
    fake_data = np.zeros((4096, 1), dtype=np.float32)

    agent._state_recording = True
    agent._callback(fake_data, 4096, None, None)

    assert not audio_queue.empty()
    chunk = audio_queue.get_nowait()
    assert chunk.shape == fake_data.shape


def test_callback_does_not_put_when_not_recording(audio_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]) -> None:
    agent = AudioAgent(audio_queue, AUDIO)
    fake_data = np.zeros((4096, 1), dtype=np.float32)

    agent._state_recording = False
    agent._callback(fake_data, 4096, None, None)

    assert audio_queue.empty()


def test_callback_copies_data(audio_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]) -> None:
    agent = AudioAgent(audio_queue, AUDIO)
    fake_data = np.ones((4096, 1), dtype=np.float32)

    agent._state_recording = True
    agent._callback(fake_data, 4096, None, None)
    fake_data[:] = 0.0

    chunk = audio_queue.get_nowait()
    assert chunk.sum() > 0.0


def test_start_creates_stream(monkeypatch: pytest.MonkeyPatch, audio_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]]) -> None:
    calls: dict[str, bool] = {"started": False, "stopped": False, "closed": False}

    class FakeStream:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def start(self) -> None:
            calls["started"] = True

        def stop(self) -> None:
            calls["stopped"] = True

        def close(self) -> None:
            calls["closed"] = True

    class FakeSoundDevice:
        @staticmethod
        def InputStream(**kwargs: object) -> FakeStream:
            return FakeStream(**kwargs)

    import src.audio_agent as audio_module

    monkeypatch.setattr(audio_module, "sd", FakeSoundDevice)

    agent = AudioAgent(audio_queue, AUDIO)
    agent.start()
    agent.stop()

    assert calls["started"] is True
    assert calls["stopped"] is True
    assert calls["closed"] is True


def test_queue_does_not_overflow() -> None:
    small_queue: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]] = queue.Queue(maxsize=5)
    agent = AudioAgent(small_queue, AUDIO)
    agent._state_recording = True

    fake_data = np.zeros((4096, 1), dtype=np.float32)
    for _ in range(10):
        agent._callback(fake_data, 4096, None, None)

    assert small_queue.qsize() == 5
