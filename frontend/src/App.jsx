import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { loadRuntimeConfig } from './config'
import { makeApiClient } from './api'
import { loadState, saveState, clearState } from './storage'
import { useAudioRecorder } from './hooks/useAudioRecorder'
import { sendVoiceTurn } from './services/voiceApi'
import { base64ToBlob, blobToFile, playAudioFromBlob } from './utils/audio'

function Header({ botName, kioskMeta, online }) {
  return (
    <div className="header">
      <div className="headerInner">
        <div className="brandBlock">
          <img className="brandLogo" src="/brand/logo.png" alt="Logo Millenium Natural Systems" />
          <div className="brandTitle">
            <h1>{botName || 'NatuBot'}</h1>
            <div className="small">Kiosco informativo</div>
          </div>
        </div>

        <div className="meta">
          <div className={`badge ${online ? '' : 'offline'}`}>{online ? 'Conectado' : 'Sin internet'}</div>
          {kioskMeta?.name && <div className="small">{kioskMeta.name}</div>}
          {kioskMeta?.location && <div className="small">{kioskMeta.location}</div>}
        </div>
      </div>
    </div>
  )
}

function TermsScreen({ terms, accepted, setAccepted, loading, onContinue }) {
  return (
    <div className="termsLayout">
      <div className="termsAside">
        <img src="/brand/bot.png" alt="NatuBot (placeholder)" />
        <div className="asideNote">
          Assets en <code>frontend/public/brand/</code>. Puedes reemplazar <b>logo.png</b> y <b>bot.png</b> por los oficiales (mismo nombre) sin tocar código.
        </div>
      </div>

      <div className="card" style={{ flex: 1 }}>
        <h2 style={{ marginTop: 0, color: 'var(--brand)' }}>Términos y Condiciones</h2>
        <div className="small">Versión: {terms?.version || '-'}</div>
        <div className="hr" />

        <div className="termsbox">
          {loading ? (
            <div className="small">Cargando términos…</div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {terms?.content_markdown || 'No fue posible cargar los términos.'}
            </ReactMarkdown>
          )}
        </div>

        <div className="hr" />

        <label className="row" style={{ gap: 10 }}>
          <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
          <span>He leído y acepto los términos.</span>
        </label>

        <div className="footerActions" style={{ marginTop: 12 }}>
          <div className="small">Para continuar debes aceptar los términos.</div>
          <button disabled={!accepted} onClick={onContinue}>Aceptar y continuar</button>
        </div>
      </div>
    </div>
  )
}

function fmtMs(ms) {
  const s = Math.max(0, Math.floor(ms / 1000))
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

function ChatScreen({ api, config, termsVersion, kioskAuthReady, botName }) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [err, setErr] = useState('')
  const [log, setLog] = useState([])
  const [lastAudioBlob, setLastAudioBlob] = useState(null)
  const [showPlayLast, setShowPlayLast] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(true)
  const [voiceDiag, setVoiceDiag] = useState({
    hadAudio: false,
    autoplayBlocked: false,
    lastError: '',
    sttMode: '-',
    fallback: false,
  })

  const chatLogRef = useRef(null)
  const seededRef = useRef(false)

  const recorder = useAudioRecorder()
  const isOnline = navigator.onLine

  useEffect(() => {
    const supports = typeof window !== 'undefined'
      && navigator?.mediaDevices?.getUserMedia
      && typeof MediaRecorder !== 'undefined'
    setVoiceSupported(Boolean(supports))
  }, [])

  useEffect(() => {
    if (seededRef.current) return
    setLog([buildWelcome()])
    seededRef.current = true
  }, [botName, config])

  useEffect(() => {
    if (!chatLogRef.current) return
    chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight
  }, [log, voiceBusy, recorder.elapsedMs])

  useEffect(() => {
    if (recorder.error) setErr(recorder.error)
  }, [recorder.error])

  const uiBusy = busy || voiceBusy || recorder.state === 'stopping'

  const micLabel = useMemo(() => {
    if (recorder.state === 'recording') return '⏹ Stop'
    if (recorder.state === 'requesting') return '🎤 Permiso…'
    if (recorder.state === 'stopping') return '⏳ Cerrando…'
    return '🎤 Start'
  }, [recorder.state])

  function buildWelcome() {
    const name = botName || 'NatuBot'
    const welcome = (config?.welcome_message && String(config.welcome_message).trim())
      || `Hola, soy ${name}.
Estoy aquí para ayudarte a conocer nuestros suplementos naturales.

¿En qué puedo ayudarte hoy?`
    return { who: name, text: welcome, source: 'system' }
  }

  function clearChat() {
    setErr('')
    setMessage('')
    setLog([buildWelcome()])
    setShowPlayLast(false)
    setLastAudioBlob(null)
    setVoiceDiag({ hadAudio: false, autoplayBlocked: false, lastError: '', sttMode: '-', fallback: false })
  }

  async function tryPlayBotAudio(blob) {
    try {
      await playAudioFromBlob(blob)
      setShowPlayLast(false)
      setVoiceDiag((d) => ({ ...d, autoplayBlocked: false, lastError: '' }))
    } catch {
      setShowPlayLast(true)
      setVoiceDiag((d) => ({ ...d, autoplayBlocked: true, lastError: 'Autoplay bloqueado por el navegador.' }))
    }
  }

  async function sendText() {
    setErr('')
    if (!isOnline) {
      setErr(config?.offline_message || 'Sin internet. Este servicio no funciona sin conexión.')
      return
    }
    if (!kioskAuthReady) {
      setErr('Este kiosco no está configurado. Revisa public/kiosk-config.json.')
      return
    }
    const q = message.trim()
    if (!q) return

    setBusy(true)
    try {
      setLog((l) => [...l, { who: 'Tú', text: q, source: 'text' }])
      setMessage('')

      const payload = {
        message: q,
        accepted_terms: true,
        accepted_terms_version: termsVersion,
        top_k: 5,
      }

      const res = await api.post('/chat', payload)
      setLog((l) => [...l, { who: (botName || 'NatuBot'), text: res.answer || '(sin respuesta)', source: 'text' }])
    } catch (e) {
      const msg = String(e.message || e)
      setErr(msg)
    } finally {
      setBusy(false)
    }
  }

  async function handleVoiceToggle() {
    setErr('')

    if (!voiceSupported) {
      setErr('Tu navegador no soporta grabación de audio. Usa Chrome/Edge reciente.')
      return
    }
    if (!isOnline) {
      setErr(config?.offline_message || 'Sin internet. Este servicio no funciona sin conexión.')
      return
    }
    if (!kioskAuthReady) {
      setErr('Este kiosco no está configurado. Revisa public/kiosk-config.json.')
      return
    }

    try {
      if (recorder.state === 'recording') {
        setVoiceBusy(true)
        const blob = await recorder.stop()
        const file = blobToFile(blob, 'turn.webm')

        const resp = await sendVoiceTurn({
          audioFile: file,
          includeAudio: true,
        })

        const userText = (resp.stt_text || '').trim() || '(no se detectó voz)'
        const botText = (resp.bot_text || '').trim() || '(sin respuesta)'

        setVoiceDiag({
          hadAudio: Boolean(resp.audio_wav_base64),
          autoplayBlocked: false,
          lastError: resp.audio_wav_base64 ? '' : 'El backend respondió sin audio_wav_base64.',
          sttMode: resp.stt_mode_used || '-',
          fallback: Boolean(resp.fallback_used),
        })

        setLog((l) => [
          ...l,
          { who: 'Tú', text: userText, source: 'voice' },
          { who: (botName || 'NatuBot'), text: botText, source: 'voice' },
        ])

        if (resp.audio_wav_base64) {
          const wavBlob = base64ToBlob(resp.audio_wav_base64, 'audio/wav')
          setLastAudioBlob(wavBlob)
          await tryPlayBotAudio(wavBlob)
        }
      } else {
        await recorder.start()
      }
    } catch (e) {
      const msg = String(e.message || e)
      setErr(msg)
    } finally {
      setVoiceBusy(false)
    }
  }

  async function playLastResponse() {
    if (!lastAudioBlob) return
    setErr('')
    try {
      await playAudioFromBlob(lastAudioBlob)
      setShowPlayLast(false)
    } catch (e) {
      const msg = `No se pudo reproducir el último audio: ${String(e.message || e)}`
      setErr(msg)
      setVoiceDiag((d) => ({ ...d, autoplayBlocked: true, lastError: msg }))
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Chat</h2>
        <button className="secondary" onClick={clearChat} disabled={uiBusy}>Limpiar</button>
      </div>

      <div className="small" style={{ marginTop: 6 }}>
        Nota: Este chat es informativo y no reemplaza a un profesional de salud.
      </div>
      <div className="small" style={{ marginTop: 6 }}>
        Mic audio is processed to answer your question.
      </div>

      <div className="voicePanel">
        <button
          className={`voiceBtn ${recorder.state === 'recording' ? 'recording' : ''}`}
          onClick={handleVoiceToggle}
          disabled={uiBusy || recorder.state === 'requesting'}
        >
          {micLabel}
        </button>

        <div className="voiceMeta">
          {recorder.state === 'recording' && <span>Recording… {fmtMs(recorder.elapsedMs)}</span>}
          {voiceBusy && <span>Processing…</span>}
          {!voiceBusy && recorder.state === 'idle' && <span>Turnos recomendados: 5–20s.</span>}
        </div>

        <div className="voiceDiag">
          <span className={`diagPill ${voiceDiag.hadAudio ? 'ok' : 'warn'}`}>Audio backend: {voiceDiag.hadAudio ? 'sí' : 'no'}</span>
          <span className={`diagPill ${voiceDiag.autoplayBlocked ? 'warn' : 'ok'}`}>Autoplay: {voiceDiag.autoplayBlocked ? 'bloqueado' : 'ok'}</span>
          <span className="diagPill">STT: {voiceDiag.sttMode}{voiceDiag.fallback ? ' (fallback local)' : ''}</span>
          {voiceDiag.lastError && <span className="diagPill warn">Detalle: {voiceDiag.lastError}</span>}
        </div>

        {showPlayLast && (
          <button className="secondary" onClick={playLastResponse}>
            ▶ Play last response
          </button>
        )}
      </div>

      <div className="hr" />

      {err && <div className="badge offline" style={{ marginBottom: 12 }}>{err}</div>}

      <div className="chatlog" ref={chatLogRef}>
        {log.length === 0 ? (
          <div className="small">Escribe una pregunta para comenzar.</div>
        ) : (
          log.map((m, i) => {
            const isUser = m.who === 'Tú'
            return (
              <div key={i} className={`msgWrap ${isUser ? 'user' : 'bot'}`}>
                {!isUser && (
                  <img className="avatar" src="/brand/bot.png" alt="NatuBot" />
                )}
                <div className={`msg ${isUser ? 'user' : 'bot'}`}>
                  <div className="who">{m.who}</div>
                  <div className="text">{m.text}</div>
                  {m.source && m.source !== 'system' && <div className="msgSource">{m.source}</div>}
                </div>
              </div>
            )
          })
        )}
      </div>

      <div className="hr" />

      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Escribe tu pregunta..."
        disabled={uiBusy}
      />

      <div className="row" style={{ justifyContent: 'space-between', marginTop: 10 }}>
        <div className="small">{config?.max_message_chars ? `Máx ${config.max_message_chars} caracteres.` : ''}</div>
        <button onClick={sendText} disabled={uiBusy || !message.trim()}>
          {busy ? 'Enviando…' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const [runtime, setRuntime] = useState(null)
  const [api, setApi] = useState(null)
  const [config, setConfig] = useState(null)
  const [terms, setTerms] = useState(null)
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [screen, setScreen] = useState('terms')
  const [loadingTerms, setLoadingTerms] = useState(true)
  const [online, setOnline] = useState(navigator.onLine)
  const [kioskAuthReady, setKioskAuthReady] = useState(false)

  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      const r = await loadRuntimeConfig()
      setRuntime(r)
      setApi(makeApiClient(r))
      setKioskAuthReady(Boolean(r.deviceId && r.kioskToken))
    })()
  }, [])

  useEffect(() => {
    const s = loadState()
    if (s?.accepted_terms && s?.accepted_terms_version) setTermsAccepted(true)
  }, [])

  useEffect(() => {
    if (!api) return
    ;(async () => {
      try { setConfig(await api.get('/config')) } catch {}
    })()
  }, [api])

  useEffect(() => {
    if (!api) return
    ;(async () => {
      setLoadingTerms(true)
      try { setTerms(await api.get('/terms')) }
      catch { setTerms(null) }
      finally { setLoadingTerms(false) }
    })()
  }, [api])

  useEffect(() => {
    if (!terms?.version) return
    const s = loadState()
    if (s?.accepted_terms && s?.accepted_terms_version && s.accepted_terms_version !== terms.version) {
      clearState()
      setTermsAccepted(false)
      setScreen('terms')
    }
  }, [terms])

  const botName = config?.bot_name || 'NatuBot'
  const kioskMeta = config?.kiosk || {}
  const acceptedVersion = (() => {
    const s = loadState()
    return s?.accepted_terms_version || terms?.version || ''
  })()

  function continueToChat() {
    const v = terms?.version
    if (!termsAccepted || !v) return
    saveState({ accepted_terms: true, accepted_terms_version: v })
    setScreen('chat')
  }

  return (
    <div className="container">
      <Header botName={botName} kioskMeta={kioskMeta} online={online} />

      {screen === 'terms' ? (
        <TermsScreen
          terms={terms}
          accepted={termsAccepted}
          setAccepted={setTermsAccepted}
          loading={loadingTerms}
          onContinue={continueToChat}
        />
      ) : (
        <ChatScreen api={api} config={config} termsVersion={acceptedVersion} kioskAuthReady={kioskAuthReady} botName={botName} />
      )}

      <div className="card">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div className="small">Config fuente: <b>{runtime?.source || '-'}</b></div>
          <div className="small">Backend: <b>{runtime?.apiBaseUrl || '-'}</b></div>
        </div>
        <div className="small" style={{ marginTop: 8 }}>
          Kiosco: crea <code>public/kiosk-config.json</code> copiando <code>kiosk-config.example.json</code>.
        </div>
      </div>
    </div>
  )
}
