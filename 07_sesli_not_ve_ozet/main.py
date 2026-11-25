"""07 - Sesli Not -> Yapılandırılmış Özet (STT + yapısal çıktı veren Agent)

Uzun uzun konuş (toplantı notu, fikir, günlük...). Program:
  1) Sesini yazıya döker (OpenAI STT modeli)
  2) Bir Agent bunu yapılandırılmış bir özete çevirir (başlık, özet, yapılacaklar)
  3) Sonucu notlar/ klasörüne Markdown dosyası olarak kaydeder
  4) Özeti sana sesli okur
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer
from common.push_to_talk import MIN_SAMPLES, record_push_to_talk, wait_for_talk

load_settings()

from agents import Agent, Runner  # noqa: E402
from agents.voice import (  # noqa: E402
    AudioInput,
    OpenAIVoiceModelProvider,
    STTModelSettings,
    TTSModelSettings,
)

NOTES_DIR = Path(__file__).resolve().parent / "notlar"


class NoteSummary(BaseModel):
    baslik: str
    ozet: str
    yapilacaklar: list[str]
    etiketler: list[str]


summarizer = Agent(
    name="NotOzetleyici",
    model=env("METIN_MODELI", "gpt-4.1-mini"),
    instructions=(
        "Kullanıcının sesli notunun dökümünü alacaksın. Türkçe olarak kısa bir başlık, "
        "2-4 cümlelik özet, varsa yapılacaklar listesi ve 1-4 etiket çıkar."
    ),
    output_type=NoteSummary,
)


def to_markdown(note: NoteSummary, transcript: str) -> str:
    todos = "\n".join(f"- [ ] {t}" for t in note.yapilacaklar) or "- (yok)"
    tags = " ".join(f"#{t.replace(' ', '_')}" for t in note.etiketler)
    return (
        f"# {note.baslik}\n\n{tags}\n\n## Özet\n{note.ozet}\n\n"
        f"## Yapılacaklar\n{todos}\n\n## Tam döküm\n{transcript}\n"
    )


async def main() -> None:
    provider = OpenAIVoiceModelProvider()
    stt = provider.get_stt_model("gpt-4o-transcribe")
    tts = provider.get_tts_model("gpt-4o-mini-tts")
    player = AudioPlayer()

    print("=== 07 - Sesli Not ve Özet ===")
    print("Enter/Boşluk: notunu söylemeye başla ve bitir | q: çıkış")

    try:
        while await wait_for_talk():
            recording = await record_push_to_talk()
            if len(recording) < MIN_SAMPLES:
                print("  (Kayıt çok kısa, tekrar dene)")
                continue

            print("  Yazıya dökülüyor...")
            try:
                transcript = await stt.transcribe(
                    AudioInput(buffer=recording),
                    STTModelSettings(language="tr"),
                    trace_include_sensitive_data=False,
                    trace_include_sensitive_audio_data=False,
                )
            except Exception as e:  # noqa: BLE001
                print(f"[HATA] {type(e).__name__}: {e}")
                continue
            if len(transcript.strip()) < 2:
                print("  (Ne dediğini anlayamadım, tekrar dene)")
                continue
            print(f"\n[Döküm]\n{transcript}\n")

            print("  Özetleniyor...")
            note: NoteSummary = (await Runner.run(summarizer, transcript)).final_output

            NOTES_DIR.mkdir(exist_ok=True)
            path = NOTES_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S}.md"
            path.write_text(to_markdown(note, transcript), encoding="utf-8")

            print(f"[Başlık] {note.baslik}\n[Özet] {note.ozet}")
            for t in note.yapilacaklar:
                print(f"  - {t}")
            print(f"  Kaydedildi: {path}\n")

            spoken = f"{note.baslik}. {note.ozet}"
            if note.yapilacaklar:
                spoken += " Yapılacaklar: " + ", ".join(note.yapilacaklar) + "."
            async for chunk in tts.run(spoken, TTSModelSettings(voice=env("ASISTAN_SESI", "coral"))):
                player.add(chunk)
            await player.wait_until_done()
    finally:
        player.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
