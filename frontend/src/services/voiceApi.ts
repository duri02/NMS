import { loadRuntimeConfig } from '../config'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

type VoiceTurnResponse = {
  stt_text: string
  bot_text: string
  audio_wav_base64?: string
}

type VoiceTurnParams = {
  audioFile: File
  includeAudio?: boolean
  signal?: AbortSignal
}

function timeoutSignal(ms: number) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), ms)
  return { signal: ctrl.signal, cancel: () => clearTimeout(timer) }
}

function mergeSignals(signals: AbortSignal[]) {
  const ctrl = new AbortController()
  const onAbort = () => ctrl.abort()

  for (const s of signals) {
    if (s.aborted) {
      ctrl.abort()
      break
    }
    s.addEventListener('abort', onAbort, { once: true })
  }

  return ctrl.signal
}

export async function sendVoiceTurn({
  audioFile,
  includeAudio = true,
  signal,
}: VoiceTurnParams): Promise<VoiceTurnResponse> {
  const runtime = await loadRuntimeConfig()
  const base = (BACKEND_URL || runtime.apiBaseUrl || '').replace(/\/$/, '')
  if (!base) throw new Error('No se encontró backend URL para voz (VITE_BACKEND_URL).')

  const fd = new FormData()
  fd.append('audio', audioFile)
  fd.append('include_audio', includeAudio ? 'true' : 'false')

  const headers: Record<string, string> = {}
  if (runtime.deviceId) headers['X-Device-Id'] = runtime.deviceId
  if (runtime.kioskToken) headers['X-Kiosk-Token'] = runtime.kioskToken

  const timeout = timeoutSignal(30_000)
  const merged = signal ? mergeSignals([signal, timeout.signal]) : timeout.signal

  try {
    const res = await fetch(`${base}/api/voice/turn`, {
      method: 'POST',
      body: fd,
      headers,
      signal: merged,
    })

    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(data?.error || data?.detail || `HTTP ${res.status}`)
    }

    return {
      stt_text: String(data?.stt_text || ''),
      bot_text: String(data?.bot_text || ''),
      audio_wav_base64: data?.audio_wav_base64 ? String(data.audio_wav_base64) : undefined,
    }
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('La solicitud de voz excedió 30s o fue cancelada.')
    }
    throw e
  } finally {
    timeout.cancel()
  }
}
