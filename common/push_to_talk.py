"""Bas-konuş (push-to-talk) için ortak klavye + kayıt yardımcıları.

Windows'ta tuşlar `msvcrt` ile doğrudan okunur:
  - Enter veya Boşluk: kaydı başlat / bitir
  - q: çıkış
Asistan düşünürken ya da konuşurken basılan tuşlar yok sayılır (sıraya girmez).
"""

from __future__ import annotations

import asyncio
import sys
import time

import numpy as np
import sounddevice as sd

from .audio import CHANNELS, DTYPE, SAMPLE_RATE, AudioPlayer

try:
    import msvcrt  # Windows
except ImportError:  # pragma: no cover - Windows dışı sistemler
    msvcrt = None

MIN_SAMPLES = SAMPLE_RATE // 4  # 0.25 saniyeden kısa kayıtları yok say


def _use_console_keys() -> bool:
    return msvcrt is not None and sys.stdin.isatty()


def _flush_keys() -> None:
    if _use_console_keys():
        while msvcrt.kbhit():
            msvcrt.getwch()


async def _read_key() -> str:
    """Bir tuş basılmasını bekler: 'talk' (Enter/Boşluk) veya 'quit' (q)."""
    if not _use_console_keys():
        # Konsol yoksa (örn. çıktı yönlendirilmişse) satır bazlı okumaya geri dön
        line = await asyncio.to_thread(sys.stdin.readline)
        return "quit" if line.strip().lower() == "q" or line == "" else "talk"

    while True:
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\r", "\n", " "):
                return "talk"
            if ch.lower() == "q":
                return "quit"
        await asyncio.sleep(0.02)


async def wait_for_talk() -> bool:
    """Kullanıcı Enter/Boşluk'a basarsa True, q'ya basarsa False döner."""
    _flush_keys()
    print("\n> Konuşmak için Enter'a (veya Boşluk'a) bas, çıkmak için q: ", end="", flush=True)
    key = await _read_key()
    print()
    return key == "talk"


async def record_push_to_talk() -> np.ndarray:
    """Kaydı başlatır, Enter/Boşluk'a tekrar basılınca bitirir."""
    frames: list[np.ndarray] = []

    def callback(indata, _frames, _time, _status) -> None:
        frames.append(indata.copy())

    _flush_keys()
    start = time.monotonic()
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=callback):
        if _use_console_keys():
            while True:
                print(
                    f"\r  ● Dinliyorum... {time.monotonic() - start:4.1f} sn  "
                    "(bitirmek için Enter/Boşluk)",
                    end="",
                    flush=True,
                )
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n", " ", "q", "Q"):
                        break
                await asyncio.sleep(0.05)
            print()
        else:
            print("  ● Dinliyorum... (bitirmek için Enter)", flush=True)
            await _read_key()

    if not frames:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate(frames).flatten()


async def run_push_to_talk_loop(pipeline, player: AudioPlayer) -> None:
    """Bas-konuş döngüsü: bekle -> kaydet -> pipeline -> çal -> tekrar."""
    from agents.voice import AudioInput  # SDK'yı .env yüklendikten sonra içe aktar

    while await wait_for_talk():
        recording = await record_push_to_talk()
        if len(recording) < MIN_SAMPLES:
            print("  (Kayıt çok kısa, tekrar dene)")
            continue

        print("  … düşünüyor", flush=True)
        try:
            result = await pipeline.run(AudioInput(buffer=recording))
            async for event in result.stream():
                if event.type == "voice_stream_event_audio" and event.data is not None:
                    player.add(event.data)
                elif event.type == "voice_stream_event_error":
                    print(f"\n[HATA] {event.error}")
        except Exception as e:  # noqa: BLE001 - tek bir turdaki hata programı kapatmasın
            print(f"\n[HATA] {type(e).__name__}: {e}")
            continue
        await player.wait_until_done()
