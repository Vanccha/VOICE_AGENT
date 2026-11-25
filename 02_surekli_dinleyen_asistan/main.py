"""02 - Sürekli Dinleyen Asistan (VoicePipeline + StreamedAudioInput)

Tuşa basmana gerek yok: mikrofon sürekli açık, sen sustuğunda asistan bunu
kendisi algılar (turn detection) ve cevap verir.
Asistan konuşurken mikrofon kısılır, böylece kendi sesini duyup karışmaz.
Çıkmak için Ctrl+C.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer, mic_stream
from common.workflows import PrintingWorkflow

load_settings()

from agents import Agent  # noqa: E402
from agents.voice import (  # noqa: E402
    StreamedAudioInput,
    STTModelSettings,
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

agent = Agent(
    name="Asistan",
    model=env("METIN_MODELI", "gpt-4.1-mini"),
    instructions=(
        "Sen sohbet etmeyi seven, meraklı bir Türkçe sesli arkadaşsın. "
        "Kısa cümlelerle konuş, ara sıra karşı tarafa soru sor. "
        "Markdown veya emoji kullanma."
    ),
)


async def feed_microphone(audio_input: StreamedAudioInput, player: AudioPlayer) -> None:
    async for chunk in mic_stream(mute_when=player.is_playing):
        await audio_input.add_audio(chunk)


async def main() -> None:
    pipeline = VoicePipeline(
        workflow=PrintingWorkflow(agent),
        config=VoicePipelineConfig(
            workflow_name="02 Surekli Dinleyen Asistan",
            trace_include_sensitive_audio_data=False,
            stt_settings=STTModelSettings(
                language="tr",
                # Sunucu tarafı konuşma bitişi algılama
                turn_detection={"type": "semantic_vad", "eagerness": "medium"},
            ),
            tts_settings=TTSModelSettings(voice=env("ASISTAN_SESI", "coral")),
        ),
    )
    player = AudioPlayer()
    audio_input = StreamedAudioInput()

    print("=== 02 - Sürekli Dinleyen Asistan ===")
    print("Konuşmaya başla, dinliyorum... (çıkış: Ctrl+C)\n")

    result = await pipeline.run(audio_input)
    mic_task = asyncio.create_task(feed_microphone(audio_input, player))
    try:
        async for event in result.stream():
            if event.type == "voice_stream_event_audio" and event.data is not None:
                player.add(event.data)
            elif event.type == "voice_stream_event_lifecycle":
                if event.event == "turn_ended":
                    print("  (dinliyorum...)")
            elif event.type == "voice_stream_event_error":
                print(f"\n[HATA] {event.error}")
    finally:
        mic_task.cancel()
        player.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
