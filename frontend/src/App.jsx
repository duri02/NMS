import React, { useEffect, useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { loadRuntimeConfig } from './config'
import { makeApiClient } from './api'
import { loadState, saveState, clearState } from './storage'

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

function ChatScreen({ api, config, termsVersion, kioskAuthReady, botName }) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [log, setLog] = useState([])


  // Seed welcome message from /config (editable without redeploy)
  const seededRef = useRef(false)

  useEffect(() => {
    if (seededRef.current) return
    setLog([buildWelcome()])
    seededRef.current = true
  }, [botName, config])

  const online = navigator.onLine

  function buildWelcome() {
    const name = botName || 'NatuBot'
    const welcome = (config?.welcome_message && String(config.welcome_message).trim())
      || `Hola, soy ${name}.
Estoy aquí para ayudarte a conocer nuestros suplementos naturales.

¿En qué puedo ayudarte hoy?`
    return { who: name, text: welcome }
  }

  function clearChat() {
    setErr('')
    setMessage('')
    setLog([buildWelcome()])
  }

  async function send() {
    setErr('')
    if (!online) {
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
      setLog((l) => [...l, { who: 'Tú', text: q }])
      setMessage('')

      const payload = {
        message: q,
        accepted_terms: true,
        accepted_terms_version: termsVersion,
        top_k: 5,
      }

      const res = await api.post('/chat', payload)
      setLog((l) => [...l, { who: (botName || 'NatuBot'), text: res.answer || '(sin respuesta)' }])
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Chat</h2>
        <button className="secondary" onClick={clearChat} disabled={busy}>Limpiar</button>
      </div>

      <div className="small" style={{ marginTop: 6 }}>
        Nota: Este chat es informativo y no reemplaza a un profesional de salud.
      </div>

      <div className="hr" />

      {err && <div className="badge offline" style={{ marginBottom: 12 }}>{err}</div>}

      <div className="chatlog">
        {log.length === 0 ? (
          <div className="small">Escribe una pregunta para comenzar.</div>
        ) : (
          log.map((m, i) => {
            const isUser = m.who === "Tú"
            return (
              <div key={i} className={`msgWrap ${isUser ? 'user' : 'bot'}`}>
                {!isUser && (
                  <img className="avatar" src="/brand/bot.png" alt="NatuBot" />
                )}
                <div className={`msg ${isUser ? 'user' : 'bot'}`}>
                  <div className="who">{m.who}</div>
                  <div className="text">{m.text}</div>
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
        disabled={busy}
      />

      <div className="row" style={{ justifyContent: 'space-between', marginTop: 10 }}>
        <div className="small">{config?.max_message_chars ? `Máx ${config.max_message_chars} caracteres.` : ''}</div>
        <button onClick={send} disabled={busy || !message.trim()}>
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

  // Force re-accept if version changes
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
