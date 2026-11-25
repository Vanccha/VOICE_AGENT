"""01 - Bas-Konuş Sesli Asistan (VoicePipeline + AudioInput)

Akış: Mikrofon -> Sesten yazıya (STT) -> Agent -> Yazıdan sese (TTS) -> Hoparlör
Enter'a basıp konuşursun, tekrar Enter'a basınca asistan cevap verir.
Konuşma geçmişi hatırlanır.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer
from common.push_to_talk import run_push_to_talk_loop
from common.workflows import PrintingWorkflow

load_settings()

from agents import Agent  # noqa: E402
from agents.voice import (  # noqa: E402
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

agent = Agent(
    name="Asistan",
    model=env("METIN_MODELI", "gpt-4.1-mini"),
    instructions=(
        "Sen samimi, yardımsever bir Türkçe sesli asistansın. "
        "Cevapların sesli okunacağı için kısa ve doğal konuş; madde işareti, emoji "
        "veya markdown kullanma."
    ),
)


async def main() -> None:
    pipeline = VoicePipeline(
        workflow=PrintingWorkflow(agent),
        config=VoicePipelineConfig(
            workflow_name="01 Bas-Konus Asistan",
            trace_include_sensitive_audio_data=False,
            tts_settings=TTSModelSettings(voice=env("ASISTAN_SESI", "coral")),
        ),
    )
    player = AudioPlayer()

    print("=== 01 - Bas-Konuş Sesli Asistan ===")
    print("Enter/Boşluk: konuşmaya başla ve bitir | q: çıkış")

    try:
        await run_push_to_talk_loop(pipeline, player)
    finally:
        player.close()
    print("Görüşürüz!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
