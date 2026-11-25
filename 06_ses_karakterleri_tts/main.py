"""06 - Ses Karakterleri Stüdyosu (sadece TTS, mikrofon gerekmez)

Yazdığın metni farklı ses + karakter talimatlarıyla seslendirir.
gpt-4o-mini-tts modeline "nasıl konuşacağını" (ton, duygu, aksan) talimatla söyleyebilirsin.
İstersen çıktıyı .wav dosyası olarak da kaydeder (ciktilar/ klasörüne).
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_settings
from common.audio import AudioPlayer, save_wav

load_settings()

from agents.voice import OpenAIVoiceModelProvider, TTSModelSettings  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "ciktilar"

CHARACTERS = {
    "1": ("Haber Spikeri", "onyx", "Ciddi, net ve otoriter bir haber spikeri gibi konuş."),
    "2": ("Masalcı Nine", "fable", "Sıcak, yavaş ve fısıltıya yakın; çocuğa masal anlatan bir nine gibi."),
    "3": ("Heyecanlı Maç Spikeri", "ash", "Çok heyecanlı, hızlı ve coşkulu bir futbol spikeri gibi bağır."),
    "4": ("Sakin Meditasyon Rehberi", "sage", "Çok sakin, yavaş, nefes aralarıyla huzur veren bir tonda."),
    "5": ("Neşeli Çocuk Programı", "coral", "Çok neşeli, enerjik ve gülümseyerek konuşan bir sunucu gibi."),
    "6": ("Korsan Kaptan", "verse", "Kaba, gür sesli, maceracı bir korsan kaptan gibi; abartılı ve eğlenceli."),
    "7": ("Robot", "echo", "Monoton, duygusuz ve mekanik bir robot gibi, kelimeleri tek tek vurgula."),
}


async def speak(text: str, voice: str, instructions: str, player: AudioPlayer) -> bytes:
    tts = OpenAIVoiceModelProvider().get_tts_model("gpt-4o-mini-tts")
    settings = TTSModelSettings(voice=voice, instructions=instructions)
    audio = bytearray()
    async for chunk in tts.run(text, settings):
        player.add(chunk)
        audio.extend(chunk)
    await player.wait_until_done()
    return bytes(audio)


async def main() -> None:
    player = AudioPlayer()
    print("=== 06 - Ses Karakterleri Stüdyosu ===\n")
    try:
        while True:
            print("Karakterler:")
            for key, (name, voice, _) in CHARACTERS.items():
                print(f"  {key}) {name}  (ses: {voice})")
            print("  0) Hepsini sırayla dinle")
            print("  q) Çıkış")
            choice = (await asyncio.to_thread(input, "Seçim: ")).strip().lower()
            if choice == "q":
                break
            if choice not in CHARACTERS and choice != "0":
                print("Geçersiz seçim.\n")
                continue

            text = await asyncio.to_thread(input, "Seslendirilecek metin: ")
            if not text.strip():
                text = "Merhaba! Bu bir ses denemesidir. Nasıl duyuluyor?"

            keys = list(CHARACTERS) if choice == "0" else [choice]
            save = (await asyncio.to_thread(input, "WAV olarak kaydedilsin mi? (e/h): ")).lower() == "e"

            for key in keys:
                name, voice, instr = CHARACTERS[key]
                print(f"  > {name} konuşuyor...")
                audio = await speak(text, voice, instr, player)
                if save:
                    OUTPUT_DIR.mkdir(exist_ok=True)
                    stamp = datetime.now().strftime("%H%M%S")
                    path = OUTPUT_DIR / f"{stamp}_{voice}.wav"
                    save_wav(path, audio)
                    print(f"    kaydedildi: {path}")
            print()
    finally:
        player.close()


if __name__ == "__main__":
    asyncio.run(main())
