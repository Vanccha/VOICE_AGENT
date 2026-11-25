"""Mikrofon ve hoparlör yardımcıları (tüm projeler ortak kullanır).

OpenAI ses modelleri 24 kHz, mono, 16-bit PCM ses bekler ve üretir.
"""

from __future__ import annotations

import asyncio
import threading
import time
import wave
from pathlib import Path
from typing import AsyncIterator, Callable

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 24000
CHANNELS = 1
DTYPE = "int16"
CHUNK_MS = 40
CHUNK_FRAMES = SAMPLE_RATE * CHUNK_MS // 1000


class AudioPlayer:
    """Arka planda çalan, kuyruklu hoparlör.

    `add()` ile ses parçası eklenir, `clear()` ile anında susturulur (söz kesme için).
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._last_audio_time = 0.0
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_FRAMES,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, outdata, frames, _time, _status) -> None:
        needed = frames * 2  # int16 = 2 bayt
        with self._lock:
            chunk = bytes(self._buffer[:needed])
            del self._buffer[:needed]
            if chunk:
                self._last_audio_time = time.monotonic()
        if len(chunk) < needed:
            chunk += b"\x00" * (needed - len(chunk))
        outdata[:] = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)

    def add(self, audio: bytes | np.ndarray) -> None:
        if isinstance(audio, np.ndarray):
            if audio.dtype != np.int16:
                audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            audio = audio.tobytes()
        with self._lock:
            self._buffer.extend(audio)
            self._last_audio_time = time.monotonic()

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def is_playing(self, tail_seconds: float = 0.4) -> bool:
        """Çalan ses varsa (veya az önce bittiyse) True döner. Yankıyı önlemek için kullanılır."""
        with self._lock:
            if self._buffer:
                return True
        return time.monotonic() - self._last_audio_time < tail_seconds

    async def wait_until_done(self) -> None:
        while self.is_playing(tail_seconds=0.2):
            await asyncio.sleep(0.05)

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


async def mic_stream(
    mute_when: Callable[[], bool] | None = None,
) -> AsyncIterator[np.ndarray]:
    """Mikrofonu sürekli dinler ve 40 ms'lik int16 parçalar üretir.

    `mute_when()` True dönerse o parça atlanır (örn. asistan konuşurken yankıyı önlemek için).
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

    def callback(indata, _frames, _time, _status) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, indata.copy().flatten())

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=CHUNK_FRAMES,
        callback=callback,
    ):
        while True:
            chunk = await queue.get()
            if mute_when is not None and mute_when():
                continue
            yield chunk


def save_wav(path: Path, audio: bytes | np.ndarray) -> None:
    """Sesi .wav dosyası olarak kaydeder."""
    if isinstance(audio, np.ndarray):
        audio = audio.astype(np.int16).tobytes()
    with wave.open(str(path), "wb") as f:
        f.setnchannels(CHANNELS)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio)
