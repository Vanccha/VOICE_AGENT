"""05 - Canlı Sesli Çevirmen (özel VoiceWorkflowBase)

SingleAgentVoiceWorkflow yerine KENDİ workflow'umuzu yazıyoruz. Bu sayede:
  - on_start() ile açılışta sesli karşılama yapıyoruz
  - Sesli komutlarla (ajan çağırmadan) hedef dili değiştiriyoruz
  - Geçmiş tutmadan her cümleyi bağımsız çeviriyoruz

Sesli komutlar:
  "dili İngilizce yap" / "dili Almanca yap" / "dili İspanyolca yap" ...
  Diğer her şey hedef dile çevrilip seslendirilir.
Çıkış: Ctrl+C
"""

import asyncio
import sys
from collections.abc import AsyncIterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer, mic_stream

load_settings()

from agents import Agent, Runner  # noqa: E402
from agents.voice import (  # noqa: E402
    StreamedAudioInput,
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
    VoiceWorkflowBase,
    VoiceWorkflowHelper,
)

LANGUAGES = {
    "ingilizce": "English",
    "almanca": "German",
    "ispanyolca": "Spanish",
    "fransızca": "French",
    "italyanca": "Italian",
    "japonca": "Japanese",
    "arapça": "Arabic",
    "rusça": "Russian",
    "türkçe": "Turkish",
}


class TranslatorWorkflow(VoiceWorkflowBase):
    def __init__(self) -> None:
        self.target_tr = "ingilizce"

    def _agent(self) -> Agent:
        target = LANGUAGES[self.target_tr]
        return Agent(
            name="Cevirmen",
            model=env("METIN_MODELI", "gpt-4.1-mini"),
            instructions=(
                f"You are a professional interpreter. Translate the user's sentence into "
                f"{target}. If the sentence is already in {target}, translate it into Turkish. "
                "Output ONLY the translation, nothing else."
            ),
        )

    async def on_start(self) -> AsyncIterator[str]:
        yield (
            "Merhaba, ben çevirmeninim. Şu an İngilizceye çeviriyorum. "
            "Dili değiştirmek için, dili Almanca yap gibi söyleyebilirsin."
        )

    async def run(self, transcription: str) -> AsyncIterator[str]:
        print(f"\n[Sen] {transcription}")
        lower = transcription.lower()

        # 1) Özel komut: ajan çağırmadan dil değiştir
        if "dili" in lower and "yap" in lower:
            for tr_name in LANGUAGES:
                if tr_name[:-1] in lower:  # "ingilizce" / "ingilizceye" ikisini de yakala
                    self.target_tr = tr_name
                    msg = f"Tamam, artık {tr_name} diline çeviriyorum."
                    print(f"[Sistem] {msg}")
                    yield msg
                    return

        # 2) Normal çeviri: ajanı çalıştır ve metni akıt
        print(f"[Ceviri -> {self.target_tr}] ", end="", flush=True)
        result = Runner.run_streamed(self._agent(), transcription)
        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            print(chunk, end="", flush=True)
            yield chunk
        print()


async def main() -> None:
    pipeline = VoicePipeline(
        workflow=TranslatorWorkflow(),
        config=VoicePipelineConfig(
            workflow_name="05 Canli Cevirmen",
            trace_include_sensitive_audio_data=False,
            tts_settings=TTSModelSettings(
                voice="sage",
                instructions="Speak clearly and naturally, like a professional interpreter.",
            ),
        ),
    )
    player = AudioPlayer()
    audio_input = StreamedAudioInput()

    print("=== 05 - Canlı Sesli Çevirmen ===")
    print("Konuş, çevireyim. Dil değiştirmek için: 'dili Almanca yap'. Çıkış: Ctrl+C\n")

    result = await pipeline.run(audio_input)

    async def feed() -> None:
        async for chunk in mic_stream(mute_when=player.is_playing):
            await audio_input.add_audio(chunk)

    mic_task = asyncio.create_task(feed())
    try:
        async for event in result.stream():
            if event.type == "voice_stream_event_audio" and event.data is not None:
                player.add(event.data)
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
