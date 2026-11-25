"""Realtime (speech-to-speech) projeleri için ortak yardımcılar."""

from __future__ import annotations

import asyncio
import sys

from agents.realtime import RealtimeSession

from .audio import AudioPlayer, mic_stream


def barge_in_enabled() -> bool:
    """`--kulaklik` argümanı verildiyse söz kesmeye izin verilir.

    Hoparlörden dinlerken mikrofon asistanın sesini duyar ve kendi kendini keser.
    Bu yüzden varsayılan olarak asistan konuşurken mikrofon kısılır.
    Kulaklık takıyorsan `python main.py --kulaklik` ile çalıştır, asistanın sözünü kesebilirsin.
    """
    return "--kulaklik" in sys.argv


async def stream_microphone(session: RealtimeSession, player: AudioPlayer) -> None:
    mute = None if barge_in_enabled() else player.is_playing
    async for chunk in mic_stream(mute_when=mute):
        await session.send_audio(chunk.tobytes())


def handle_common_event(event, player: AudioPlayer) -> None:
    """Ses çalma, söz kesme ve konuşma dökümü gibi ortak olayları işler."""
    if event.type == "audio":
        player.add(event.audio.data)
    elif event.type == "audio_interrupted":
        player.clear()
        print("\n  (sözü kesildi)")
    elif event.type == "tool_start":
        print(f"\n  [araç çağrılıyor] {event.tool.name}({event.arguments})")
    elif event.type == "tool_end":
        print(f"  [araç sonucu] {event.output}")
    elif event.type == "handoff":
        print(f"\n  [aktarım] {event.from_agent.name} -> {event.to_agent.name}")
    elif event.type == "error":
        print(f"\n[HATA] {event.error}")
    elif event.type == "raw_model_event":
        data = event.data
        if data.type == "input_audio_transcription_completed" and data.transcript.strip():
            print(f"\n[Sen] {data.transcript.strip()}")
        elif data.type == "transcript_delta":
            print(data.delta, end="", flush=True)
        elif data.type == "turn_started":
            print("\n[Asistan] ", end="", flush=True)


async def cancel(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        pass
