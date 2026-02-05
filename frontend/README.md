# Frontend — NatuBot Kiosk (Vite + React + PWA)

## Config por kiosco
Copia:
- `public/kiosk-config.example.json` → `public/kiosk-config.json`

Edita:
- `apiBaseUrl` (tu backend FastAPI)
- `deviceId` (ej: KIOSK_001)
- `kioskToken` (token en kiosks.json del backend)

## Variables de entorno
Copia `frontend/.env.example` a `frontend/.env`:

```bash
copy .env.example .env
```

Disponible:
- `VITE_BACKEND_URL=http://localhost:8000`
  - URL backend usada para el endpoint de voz `/api/voice/turn`.
  - Si no se define, se usa `apiBaseUrl` desde `kiosk-config.json`.

## Run
```bash
npm install
npm run dev
```

Build:
```bash
npm run build
npm run preview
```

## Probar voz
1. Inicia backend y frontend.
2. Abre Chrome/Edge y permite acceso al micrófono.
3. En la pantalla de chat usa:
   - `🎤 Start` para grabar
   - `⏹ Stop` para enviar el turno
4. Si autoplay falla, usa `▶ Play last response`.
5. Revisa los indicadores del panel de voz: `Audio backend`, `Autoplay` y `STT` para diagnóstico rápido.

## Notas kiosk
- Recomendado Chrome en modo kiosk con permisos de micrófono preconcedidos.
- No se guarda audio crudo en consola; solo se procesa para responder preguntas.
