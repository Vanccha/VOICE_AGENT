"""08 - Realtime Sesli Asistan (speech-to-speech, en düşük gecikme)

Pipeline projelerinden farkı: ses araya metin koymadan doğrudan realtime modele gider,
model de doğrudan ses üretir. Çok daha hızlı ve doğal; tonlama, gülme vs. korunur.

Özellikler: anlık cevap, araç kullanma, söz kesme (kulaklıkla), canlı döküm.

Çalıştırma:
  python main.py              -> hoparlör (asistan konuşurken mikrofon kısılır)
  python main.py --kulaklik   -> kulaklık (istediğin an sözünü kesebilirsin)
Çıkış: Ctrl+C
"""

import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer
from common.realtime_helpers import (
    barge_in_enabled,
    cancel,
    handle_common_event,
    stream_microphone,
)

load_settings()

from agents import function_tool  # noqa: E402
from agents.realtime import RealtimeAgent, RealtimeRunner  # noqa: E402


@function_tool
def saat_kac() -> str:
    """Şu anki saati ve tarihi döner."""
    return datetime.now().strftime("%d.%m.%Y %H:%M")


@function_tool
def zar_at(adet: int = 1) -> str:
    """Zar atar.

    Args:
        adet: Kaç zar atılacağı.
    """
    return ", ".join(str(random.randint(1, 6)) for _ in range(max(1, min(adet, 10))))


@function_tool
def fikra_anlat() -> str:
    """Rastgele kısa bir Temel fıkrası konusu döner; asistan bunu kendi diliyle anlatır."""
    return random.choice(
        [
            "Temel'in uçağa ilk binişi ve pencere kenarı kavgası",
            "Temel ile Dursun'un balık tutarken yer işaretlemesi",
            "Temel'in bilgisayara virüs bulaştı diye ilaç alması",
        ]
    )


agent = RealtimeAgent(
    name="Asistan",
    instructions=(
        "Sen enerjik, esprili ve samimi bir Türkçe sesli asistansın. Kısa ve doğal konuş, "
        "gerektiğinde araçları kullan. Kullanıcı sözünü keserse hemen dur ve onu dinle."
    ),
    tools=[saat_kac, zar_at, fikra_anlat],
)


async def main() -> None:
    runner = RealtimeRunner(
        agent,
        config={
            "model_settings": {
                "model_name": env("REALTIME_MODELI", "gpt-realtime"),
                "voice": "marin",
                "modalities": ["audio"],
                "input_audio_transcription": {"model": "gpt-4o-mini-transcribe", "language": "tr"},
                "turn_detection": {"type": "semantic_vad", "interrupt_response": True},
            }
        },
    )
    player = AudioPlayer()

    print("=== 08 - Realtime Sesli Asistan ===")
    mode = "kulaklık (söz kesme açık)" if barge_in_enabled() else "hoparlör (söz kesme kapalı)"
    print(f"Mod: {mode}")
    print("Dene: 'Saat kaç?', 'İki zar at', 'Bir fıkra anlat'. Çıkış: Ctrl+C\n")

    session = await runner.run()
    async with session:
        mic_task = asyncio.create_task(stream_microphone(session, player))
        try:
            async for event in session:
                handle_common_event(event, player)
        finally:
            await cancel(mic_task)
            player.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
