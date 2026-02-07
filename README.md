# NatuBot — V8 (Chat + Voice pipeline offline-first)

Este repo contiene:
- `app/` + `natubot_core/`: Backend FastAPI (Gemini + Pinecone) con:
  - `/terms` (términos versionados)
  - rate limiting básico en `/chat` y `/api/voice/turn`
  - auth por kiosco con `X-Device-Id` + `X-Kiosk-Token`
  - logging en `logs/natubot_api.log`
  - pipeline de voz por turnos (`/api/voice/turn`) con STT/TTS
- `frontend/`: Vite + React + PWA (kiosco) con pantalla de términos + chat
- `notebooks/`: Ingest / walkthrough (RAG)
- `scripts/`: scripts auxiliares (ej. descarga de modelo Vosk)

---

## 1) Backend (FastAPI)

### Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env   # o duplica el archivo
# pega tus keys + configura Pinecone (PINECONE_INDEX_HOST recomendado)
```

### Dependencias opcionales / sistema
- `ffmpeg` en PATH para convertir formatos de audio distintos de WAV.
- Modelo Vosk español en `models/vosk-es`.

### Descarga de modelo Vosk (es)
```bash
python scripts/download_vosk_es_model.py --target models
```
Esto deja el modelo en `models/vosk-es`.

### Ejecutar API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints
- `GET /` (root)
- `GET /config` (config para frontend)
- `GET /terms` (términos con versión)
- `GET /health` (health JSON-safe)
- `POST /chat` (RAG texto)
- `POST /api/voice/turn` (turno de voz STT + chat + TTS, compat: `/voice/turn`)
- `POST /api/tts` (solo TTS, compat: `/tts`)

### Auth por kiosco
Headers requeridos (si `REQUIRE_KIOSK_AUTH=true`):
- `X-Device-Id: KIOSK_001`
- `X-Kiosk-Token: <token>`

Tokens en `kiosks.json`.

---

## 2) Speech pipeline (offline-first)

### Flujo por turno
1. Ingesta de audio (multipart o base64 JSON)
2. Normalización a PCM mono 16kHz
3. VAD (webrtcvad) opcional para fin de habla
4. STT (`Vosk` local o `Azure` cloud)
5. Chat/LLM existente (`answer_with_rag`)
6. TTS (`Silero` local)
7. Respuesta JSON con texto y audio base64 opcional

### Variables de entorno de voz
```env
STT_MODE=local                 # local | azure | disabled
TTS_MODE=silero                # preparado para futuro
MODELS_DIR=models
VOSK_MODEL_PATH=models/vosk-es
AUDIO_SAMPLE_RATE=16000
VAD_ENABLED=true
VAD_AGGRESSIVENESS=2
VAD_FRAME_MS=30
VAD_END_SILENCE_MS=800

AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_SPEECH_LANGUAGE=es-ES

SILERO_LANGUAGE=es
SILERO_SPEAKER=v3_es
TTS_CHUNK_CHARS=700

# Placeholder futuro
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

### Estrategia de fallback STT
- `STT_MODE=local`: intenta `Vosk` primero (opción gratis) y, si falla y Azure está configurado, usa Azure como respaldo.
- `STT_MODE=azure`: intenta Azure primero y, si falla, cae a `Vosk` si está disponible.
- `STT_MODE=disabled`: desactiva STT y permite probar solo TTS en `/api/tts` (útil para ahorrar memoria durante pruebas).

> Recomendado para empezar gratis: mantener `STT_MODE=local` y configurar Azure más adelante como respaldo premium.

---

## 3) Pruebas de voz (curl)

### A) multipart (archivo)
```bash
curl -X POST "http://localhost:8000/api/voice/turn" \
  -H "X-Device-Id: KIOSK_001" \
  -H "X-Kiosk-Token: tu_token" \
  -F "include_audio=true" \
  -F "top_k=5" \
  -F "audio=@sample.wav"
```

### B) JSON base64
```bash
# Linux/macOS
B64=$(base64 -w 0 sample.wav)
curl -X POST "http://localhost:8000/api/voice/turn" \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: KIOSK_001" \
  -H "X-Kiosk-Token: tu_token" \
  -d "{\"audio_base64\":\"$B64\",\"filename\":\"sample.wav\",\"include_audio\":true}"
```

### C) Solo TTS
```bash
curl -X POST "http://localhost:8000/api/tts" \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: KIOSK_001" \
  -H "X-Kiosk-Token: tu_token" \
  -d '{"text":"Hola, esta es una prueba de voz.","as_base64":true}'
```

### Cómo generar `sample.wav`
- Graba un audio mono 16kHz PCM (5–20s por turno) en cualquier app de grabación.
- Si tienes ffmpeg:
```bash
ffmpeg -i input_audio.m4a -ac 1 -ar 16000 sample.wav
```

---

## 4) Frontend (Vite + React + PWA)

### Setup
```bash
cd frontend
npm install
copy .env.example .env
copy public\kiosk-config.example.json public\kiosk-config.json
# edita kiosk-config.json con apiBaseUrl, deviceId y kioskToken
# opcional: VITE_BACKEND_URL en .env para endpoint de voz
npm run dev
```

Abre:
- Front: http://localhost:5173
- Docs backend: http://localhost:8000/docs

### Voz en frontend
- Botón `🎤 Start / ⏹ Stop` para turnos de voz (5–20s).
- Envía multipart a `POST /api/voice/turn`.
- Muestra `stt_text` y `bot_text` en el historial.
- Reproduce audio TTS de respuesta; si autoplay falla, muestra botón `▶ Play last response`.
- Recomendado Chrome/Edge con permisos de micrófono habilitados.

---

## 5) Nota kiosco (sin internet)
La UI muestra un mensaje “Sin internet…” y bloquea el chat cuando no hay conexión (por diseño).
