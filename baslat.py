"""Tüm ses projelerini tek yerden başlatan menü.

Çalıştır:  .venv\\Scripts\\python baslat.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PROJECTS = [
    ("01_bas_konus_asistan", "main.py", "Bas-konuş sesli asistan (Pipeline, AudioInput)"),
    ("02_surekli_dinleyen_asistan", "main.py", "Sürekli dinleyen asistan (StreamedAudioInput)"),
    ("03_aracli_asistan", "main.py", "Araç kullanan asistan (hava, hesap, not)"),
    ("04_cok_ajanli_cagri_merkezi", "main.py", "Çok ajanlı çağrı merkezi (handoff)"),
    ("05_canli_cevirmen", "main.py", "Canlı çevirmen (özel VoiceWorkflow)"),
    ("06_ses_karakterleri_tts", "main.py", "Ses karakterleri stüdyosu (sadece TTS)"),
    ("07_sesli_not_ve_ozet", "main.py", "Sesli not -> özet (STT + yapısal çıktı)"),
    ("08_realtime_asistan", "main.py", "Realtime asistan (speech-to-speech)"),
    ("09_realtime_pizza_siparis", "main.py", "Realtime pizza hattı (handoff+guardrail+onay)"),
    ("10_tarayici_realtime_web", "server.py", "Tarayıcıda realtime ajan (WebRTC, JS SDK)"),
]


def main() -> None:
    while True:
        print("\n=== VOICE_AGENT Projeleri ===")
        for i, (_, _, desc) in enumerate(PROJECTS, 1):
            print(f"  {i:>2}) {desc}")
        print("   q) Çıkış")
        choice = input("Seçim: ").strip().lower()
        if choice == "q":
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(PROJECTS):
            print("Geçersiz seçim.")
            continue

        folder, script, _ = PROJECTS[int(choice) - 1]
        args = [sys.executable, script]
        if folder.startswith(("08", "09")):
            if input("Kulaklık takıyor musun? (söz kesme açılır) (e/h): ").strip().lower() == "e":
                args.append("--kulaklik")
        try:
            subprocess.run(args, cwd=ROOT / folder)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
