"""03 - Araç Kullanan Sesli Asistan (function tools)

Asistan konuşurken gerçek fonksiyonlar çağırabilir:
  - Saat / tarih söyleme
  - Gerçek hava durumu (Open-Meteo, anahtar gerektirmez)
  - Hesap makinesi
  - Sesli not alma ve notları okuma (notlar.txt dosyasına yazar)

Örnek: "İstanbul'da hava nasıl?", "128 çarpı 37 kaç eder?",
       "Not al: yarın saat 10'da toplantı var", "Notlarımı oku"
"""

import ast
import asyncio
import operator
import sys
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings
from common.audio import AudioPlayer
from common.push_to_talk import run_push_to_talk_loop
from common.workflows import PrintingWorkflow

load_settings()

from agents import Agent, function_tool  # noqa: E402
from agents.voice import (  # noqa: E402
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

NOTES_FILE = Path(__file__).resolve().parent / "notlar.txt"

WEATHER_CODES = {
    0: "açık", 1: "çoğunlukla açık", 2: "parçalı bulutlu", 3: "kapalı",
    45: "sisli", 48: "kırağılı sis", 51: "hafif çisenti", 53: "çisenti",
    55: "yoğun çisenti", 61: "hafif yağmurlu", 63: "yağmurlu", 65: "şiddetli yağmurlu",
    71: "hafif karlı", 73: "karlı", 75: "yoğun karlı", 80: "sağanak yağışlı",
    81: "sağanak yağışlı", 82: "şiddetli sağanak", 95: "gök gürültülü fırtına",
}


@function_tool
def saat_ve_tarih() -> str:
    """Şu anki yerel saati ve tarihi döner."""
    now = datetime.now()
    return now.strftime("Tarih: %d.%m.%Y, Saat: %H:%M")


@function_tool
async def hava_durumu(sehir: str) -> str:
    """Bir şehrin anlık hava durumunu getirir.

    Args:
        sehir: Şehir adı, örn. "İstanbul".
    """
    async with httpx.AsyncClient(timeout=10) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": sehir, "count": 1, "language": "tr"},
        )
        results = geo.json().get("results")
        if not results:
            return f"{sehir} adında bir yer bulamadım."
        place = results[0]
        weather = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,wind_speed_10m,weather_code",
            },
        )
        cur = weather.json()["current"]
    desc = WEATHER_CODES.get(cur["weather_code"], "değişken")
    return (
        f"{place['name']}: {cur['temperature_2m']} derece, {desc}, "
        f"rüzgar {cur['wind_speed_10m']} km/s."
    )


_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Desteklenmeyen ifade")


@function_tool
def hesapla(ifade: str) -> str:
    """Matematiksel bir ifadeyi hesaplar.

    Args:
        ifade: Python biçiminde ifade, örn. "128 * 37" veya "(5 + 3) / 2".
    """
    try:
        return str(_safe_eval(ast.parse(ifade, mode="eval").body))
    except Exception as e:  # noqa: BLE001
        return f"Hesaplayamadım: {e}"


@function_tool
def not_al(metin: str) -> str:
    """Kullanıcının söylediği notu dosyaya kaydeder.

    Args:
        metin: Kaydedilecek not.
    """
    stamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {metin}\n")
    return "Not kaydedildi."


@function_tool
def notlari_oku() -> str:
    """Kaydedilmiş tüm notları döner."""
    if not NOTES_FILE.exists():
        return "Henüz hiç not yok."
    return NOTES_FILE.read_text(encoding="utf-8")


agent = Agent(
    name="AracliAsistan",
    model=env("METIN_MODELI", "gpt-4.1-mini"),
    instructions=(
        "Sen araç kullanabilen Türkçe bir sesli asistansın. Saat, hava durumu, hesaplama "
        "ve not işlemleri için mutlaka araçları kullan, tahmin yürütme. "
        "Cevapların sesli okunacak: kısa konuş, markdown kullanma."
    ),
    tools=[saat_ve_tarih, hava_durumu, hesapla, not_al, notlari_oku],
)


async def main() -> None:
    pipeline = VoicePipeline(
        workflow=PrintingWorkflow(agent),
        config=VoicePipelineConfig(
            workflow_name="03 Aracli Asistan",
            trace_include_sensitive_audio_data=False,
            tts_settings=TTSModelSettings(voice=env("ASISTAN_SESI", "coral")),
        ),
    )
    player = AudioPlayer()

    print("=== 03 - Araç Kullanan Sesli Asistan ===")
    print("Dene: 'Ankara'da hava nasıl?', '45 çarpı 12', 'Not al: süt al', 'Notlarımı oku'")
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
