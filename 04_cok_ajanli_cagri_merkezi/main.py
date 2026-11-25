"""04 - Çok Ajanlı Sesli Çağrı Merkezi (handoffs)

Bir "Karşılama" ajanı seni dinler ve doğru uzmana aktarır:
  - Restoran Rezervasyon ajanı  (rezervasyon kaydeder -> rezervasyonlar.json)
  - Teknik Destek ajanı         (internet / bilgisayar sorunları)
  - İngilizce Pratik ajanı      (seninle İngilizce konuşur, hatalarını düzeltir)

Örnek: "Yarın akşam 4 kişilik masa ayırtmak istiyorum",
       "İnternetim çok yavaş", "İngilizce pratik yapmak istiyorum"
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer
from common.push_to_talk import run_push_to_talk_loop
from common.workflows import PrintingWorkflow

load_settings()

from agents import Agent, function_tool  # noqa: E402
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions  # noqa: E402
from agents.voice import (  # noqa: E402
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

MODEL = env("METIN_MODELI", "gpt-4.1-mini")
RESERVATIONS_FILE = Path(__file__).resolve().parent / "rezervasyonlar.json"
SPEECH_RULE = " Cevapların sesli okunacak: kısa konuş, markdown ve emoji kullanma."


@function_tool
def rezervasyon_yap(isim: str, tarih: str, saat: str, kisi_sayisi: int) -> str:
    """Restoran rezervasyonu kaydeder.

    Args:
        isim: Rezervasyon sahibinin adı.
        tarih: Rezervasyon tarihi (örn. "yarın" veya "12 Aralık").
        saat: Rezervasyon saati (örn. "20:00").
        kisi_sayisi: Kişi sayısı.
    """
    data = json.loads(RESERVATIONS_FILE.read_text("utf-8")) if RESERVATIONS_FILE.exists() else []
    no = len(data) + 1
    data.append({"no": no, "isim": isim, "tarih": tarih, "saat": saat, "kisi": kisi_sayisi})
    RESERVATIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    return f"Rezervasyon oluşturuldu. Rezervasyon numarası: {no}"


@function_tool
def ariza_kaydi_ac(sorun: str) -> str:
    """Teknik sorun için arıza kaydı açar.

    Args:
        sorun: Sorunun kısa açıklaması.
    """
    return f"Arıza kaydı açıldı (kayıt no: TD-{abs(hash(sorun)) % 10000:04d})."


rezervasyon_ajani = Agent(
    name="Rezervasyon",
    model=MODEL,
    handoff_description="Restoran masa rezervasyonu yapan ajan.",
    instructions=prompt_with_handoff_instructions(
        "Sen 'Lezzet Durağı' restoranının rezervasyon görevlisisin. İsim, tarih, saat ve "
        "kişi sayısını tek tek sor, hepsi tamamlanınca rezervasyon_yap aracını kullan."
        + SPEECH_RULE
    ),
    tools=[rezervasyon_yap],
)

destek_ajani = Agent(
    name="TeknikDestek",
    model=MODEL,
    handoff_description="İnternet, bilgisayar ve telefon sorunlarına yardım eden ajan.",
    instructions=prompt_with_handoff_instructions(
        "Sen sabırlı bir teknik destek uzmanısın. Sorunu adım adım çözmeye çalış, her "
        "seferinde tek bir adım söyle. Çözülmezse ariza_kaydi_ac aracını kullan."
        + SPEECH_RULE
    ),
    tools=[ariza_kaydi_ac],
)

ingilizce_ajani = Agent(
    name="IngilizceOgretmeni",
    model=MODEL,
    handoff_description="Kullanıcıyla İngilizce konuşma pratiği yapan öğretmen.",
    instructions=prompt_with_handoff_instructions(
        "You are a friendly English conversation teacher. Speak only in simple English. "
        "If the user makes a mistake, gently correct it, then continue the conversation "
        "with a question. Keep answers short, no markdown."
    ),
)

karsilama_ajani = Agent(
    name="Karsilama",
    model=MODEL,
    instructions=prompt_with_handoff_instructions(
        "Sen bir çağrı merkezinin karşılama görevlisisin. Kullanıcının ne istediğini anla "
        "ve hemen doğru uzmana aktar: rezervasyon, teknik destek veya İngilizce pratik. "
        "Ne istediği belli değilse kısaca bu üç seçeneği say." + SPEECH_RULE
    ),
    handoffs=[rezervasyon_ajani, destek_ajani, ingilizce_ajani],
)

# Uzmanlar işi bitince ya da konu değişince karşılamaya geri dönebilsin
for uzman in (rezervasyon_ajani, destek_ajani, ingilizce_ajani):
    uzman.handoffs.append(karsilama_ajani)


async def main() -> None:
    pipeline = VoicePipeline(
        workflow=PrintingWorkflow(karsilama_ajani),
        config=VoicePipelineConfig(
            workflow_name="04 Cok Ajanli Cagri Merkezi",
            trace_include_sensitive_audio_data=False,
            tts_settings=TTSModelSettings(voice=env("ASISTAN_SESI", "coral")),
        ),
    )
    player = AudioPlayer()

    print("=== 04 - Çok Ajanlı Sesli Çağrı Merkezi ===")
    print("Dene: 'Masa ayırtmak istiyorum' / 'İnternetim yavaş' / 'İngilizce pratik yapalım'")
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
