"""10 - Tarayıcıda Realtime Sesli Ajan (WebRTC + JavaScript Agents SDK)

Bu proje iki parçadan oluşur:
  - server.py  : Python sunucusu. Gerçek API anahtarın SADECE burada (ortak .env'den) kalır.
                 Tarayıcıya 1 dakikalık geçici (ephemeral) anahtar üretir.
  - index.html : Tarayıcıda çalışan @openai/agents-realtime (JS SDK) ile WebRTC bağlantısı.
                 Mikrofon/hoparlör, söz kesme ve yankı engelleme tarayıcı tarafından yapılır.

Çalıştır:  python server.py   -> tarayıcıda http://localhost:8000 adresini aç
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import env, load_settings

load_settings()

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

HERE = Path(__file__).resolve().parent
app = FastAPI()
client = AsyncOpenAI()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(HERE / "index.html")


@app.post("/token")
async def token() -> dict:
    """Tarayıcı için kısa ömürlü realtime anahtarı üretir (gerçek anahtar asla tarayıcıya gitmez)."""
    secret = await client.realtime.client_secrets.create(
        expires_after={"anchor": "created_at", "seconds": 60},
        session={"type": "realtime", "model": env("REALTIME_MODELI", "gpt-realtime")},
    )
    return {"key": secret.value, "model": env("REALTIME_MODELI", "gpt-realtime")}


if __name__ == "__main__":
    print("Tarayıcıda aç: http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
