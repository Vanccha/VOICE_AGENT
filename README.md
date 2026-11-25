# VOICE_AGENT: OpenAI Agents SDK sesli ajan denemeleri

Bu klasörde 10 farklı sesli ajan projesi var. Hepsi **tek bir API anahtarı** ve **tek bir Python ortamı** kullanır.

## 1. Kurulum (tek sefer)

Python 3.10 veya üstü gerekir. PowerShell'de:

```powershell
git clone https://github.com/Vanccha/VOICE_AGENT.git
cd VOICE_AGENT
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

## 2. API anahtarını gir (tek sefer)

`.env` dosyasını aç ve şu satırı düzenle:

```
OPENAI_API_KEY=sk-...senin-anahtarın...
```

Bütün projeler anahtarı bu dosyadan okur. Aynı dosyada asistanın sesini (`ASISTAN_SESI`) ve kullanılan modelleri de değiştirebilirsin. `.env` dosyası `.gitignore` içinde olduğu için GitHub'a gönderilmez.

## 3. Çalıştır

```powershell
.\.venv\Scripts\python baslat.py
```

Açılan menüden projeyi seç. Bir projeyi doğrudan da çalıştırabilirsin:

```powershell
cd 03_aracli_asistan
..\.venv\Scripts\python main.py
```

## Projeler

| # | Klasör | Türü | Gösterdiği özellik |
|---|---|---|---|
| 01 | `01_bas_konus_asistan` | Pipeline | `VoicePipeline` ve `AudioInput`: Enter'a bas, konuş, cevap al (konuşma geçmişi tutulur) |
| 02 | `02_surekli_dinleyen_asistan` | Pipeline | `StreamedAudioInput`: mikrofon sürekli açık, sustuğunda otomatik cevap verir |
| 03 | `03_aracli_asistan` | Pipeline | `function_tool`: gerçek hava durumu, hesap makinesi, saat, sesli not alma |
| 04 | `04_cok_ajanli_cagri_merkezi` | Pipeline | **Handoff**: karşılama ajanı seni rezervasyon, teknik destek veya İngilizce öğretmeni ajanına aktarır |
| 05 | `05_canli_cevirmen` | Pipeline | Özel `VoiceWorkflowBase`: `on_start` ile açılış selamı ve sesli komutla dil değiştirme |
| 06 | `06_ses_karakterleri_tts` | Sadece TTS | Yazdığın metni 7 farklı karakterle seslendirir, istersen WAV olarak kaydeder (mikrofon gerekmez) |
| 07 | `07_sesli_not_ve_ozet` | STT ve Agent | Sesli notu yazıya döker, yapılandırılmış özet çıkarır, `.md` olarak kaydeder, özeti sesli okur |
| 08 | `08_realtime_asistan` | Realtime | `RealtimeAgent`: speech-to-speech, en düşük gecikme, araç kullanımı, söz kesme |
| 09 | `09_realtime_pizza_siparis` | Realtime | Handoff, **output guardrail** (gizli kod sızıntısını engeller) ve **araç onayı** (siparişi sen onaylarsın) |
| 10 | `10_tarayici_realtime_web` | Realtime (web) | JS Agents SDK ve WebRTC ile tarayıcıda çalışır, geçici anahtar Python sunucusundan alınır |

### Pipeline ile Realtime arasındaki fark

- **Pipeline (01–07):** Ses önce yazıya çevrilir, ardından normal bir `Agent` çalışır, cevap da sese çevrilir. Her adım kontrol edilebilir ve istenen metin modeli kullanılabilir, ama biraz daha yavaştır.
- **Realtime (08–10):** Ses doğrudan realtime modele gider, cevap da doğrudan ses olarak gelir. Çok daha hızlı ve doğaldır, araya girip sözünü kesebilirsin.

## İpuçları

- **Kulaklık:** 08 ve 09'u hoparlörle çalıştırırsan asistan konuşurken mikrofon kısılır, aksi halde kendi sesini duyar. Kulaklıkla `python main.py --kulaklik` diye çalıştırırsan istediğin an sözünü kesebilirsin. Proje 10'da tarayıcı yankıyı kendisi engeller.
- **Mikrofon izni:** Windows'ta *Ayarlar → Gizlilik → Mikrofon* altında masaüstü uygulamalarının mikrofona erişimi açık olmalı.
- **İzleme (tracing):** Tüm çalışmalar https://platform.openai.com/traces adresinde görünür.
- **Telefon hattı (sonraki adım):** Realtime ajanlar Twilio veya SIP üzerinden telefona da bağlanabilir (`OpenAIRealtimeSIPModel`). Bunun için bir Twilio hesabı gerekir.
