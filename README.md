# NatuBot — V7 (Brand CSS: azul corporativo sobre blanco)

Este repo contiene:
- `app/` + `natubot_core/`: Backend FastAPI (Gemini + Pinecone) con:
  - `/terms` (términos versionados)
  - rate limiting básico en `/chat`
  - auth por kiosco con `X-Device-Id` + `X-Kiosk-Token`
  - logging en `logs/natubot_api.log`
- `frontend/`: Vite + React + PWA (kiosco) con pantalla de términos + chat
- `notebooks/`: Ingest / walkthrough (RAG)

---

## 1) Backend (FastAPI)

### Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env   # o duplica el archivo
# pega tus keys + configura Pinecone (PINECONE_INDEX_HOST recomendado)

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints
- `GET /` (root)
- `GET /config` (config para frontend)
- `GET /terms` (términos con versión)
- `GET /health` (health JSON-safe)
- `POST /chat` (RAG)

### Auth por kiosco
Headers requeridos (si `REQUIRE_KIOSK_AUTH=true`):
- `X-Device-Id: KIOSK_001`
- `X-Kiosk-Token: <token>`

Tokens en `kiosks.json`.

---

## 2) Frontend (Vite + React + PWA)

### Setup
```bash
cd frontend
npm install
copy public\kiosk-config.example.json public\kiosk-config.json
# edita kiosk-config.json con apiBaseUrl, deviceId y kioskToken
npm run dev
```

Abre:
- Front: http://localhost:5173
- Docs backend: http://localhost:8000/docs

---

## 3) Nota kiosco (sin internet)
La UI muestra un mensaje “Sin internet…” y bloquea el chat cuando no hay conexión (por diseño).


## Novedades V6
- /config ahora incluye `welcome_message` y `welcome_message_version` para controlar el saludo inicial desde backend sin redeploy del frontend.


---

## 4) Placeholders de marca (reemplazables)

Para cumplir con el manual de marca, el frontend quedó en estilo **azul corporativo sobre blanco**.

### Archivos a reemplazar (sin cambiar el código)

- `frontend/public/brand/logo-placeholder.svg`
  - Reemplázalo por el logo oficial (mismo nombre, o ajusta la ruta en `frontend/src/App.jsx`).
- `frontend/public/brand/bot-placeholder.svg`
  - Reemplázalo por la ilustración/mascota oficial de NatuBot.

### Dónde se usan

- Header (logo): `frontend/src/App.jsx` → componente `Header`
- Pantalla de términos (ilustración): `frontend/src/App.jsx` → componente `TermsScreen`

### Colores (CSS)

- Variables en `frontend/src/styles.css` (bloque `:root`):
  - `--brand` = azul principal
  - `--brand2` = acento
