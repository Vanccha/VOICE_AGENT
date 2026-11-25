"""Ortak ayar yükleyici.

Tüm projeler API anahtarını VOICE_AGENT klasöründeki TEK bir `.env` dosyasından okur.
Anahtarı sadece orada değiştirmen yeterli.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


def load_settings() -> None:
    """Kök klasördeki .env dosyasını yükler ve API anahtarını kontrol eder."""
    load_dotenv(ENV_FILE, override=True)

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("buraya"):
        print(
            "\n[HATA] OpenAI API anahtarı bulunamadı.\n"
            f"Lütfen şu dosyayı aç ve anahtarını yaz:\n  {ENV_FILE}\n"
            "Örnek satır:  OPENAI_API_KEY=sk-...\n"
        )
        sys.exit(1)


def env(name: str, default: str) -> str:
    """.env içindeki isteğe bağlı bir ayarı okur (yoksa varsayılanı döner)."""
    value = os.getenv(name, "").strip()
    return value or default
