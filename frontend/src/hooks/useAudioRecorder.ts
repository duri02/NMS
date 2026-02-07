import { useEffect, useRef, useState } from 'react'

type RecorderState = 'idle' | 'requesting' | 'recording' | 'stopping' | 'error'

const MAX_TURN_MS = 20_000

function pickMimeType() {
  const preferred = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
  ]

  for (const mime of preferred) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mime)) return mime
  }
  return ''
}

export function useAudioRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [error, setError] = useState<string>('')
  const [elapsedMs, setElapsedMs] = useState(0)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const startedAtRef = useRef<number>(0)
  const timerRef = useRef<number | null>(null)
  const maxTimerRef = useRef<number | null>(null)
  const stopResolverRef = useRef<((blob: Blob) => void) | null>(null)
  const stopRejecterRef = useRef<((err: Error) => void) | null>(null)

  const cleanupTimers = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (maxTimerRef.current) {
      window.clearTimeout(maxTimerRef.current)
      maxTimerRef.current = null
    }
  }

  const cleanupStream = () => {
    const s = streamRef.current
    if (s) s.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  const finishIdle = () => {
    cleanupTimers()
    cleanupStream()
    mediaRecorderRef.current = null
    chunksRef.current = []
    startedAtRef.current = 0
    setElapsedMs(0)
  }

  async function start() {
    if (state === 'recording' || state === 'requesting') return

    setError('')
    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mimeType = pickMimeType()
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)

      chunksRef.current = []
      recorder.ondataavailable = (evt) => {
        if (evt.data && evt.data.size > 0) chunksRef.current.push(evt.data)
      }

      recorder.onerror = () => {
        setError('Falló la grabación de audio.')
        setState('error')
        finishIdle()
      }

      recorder.start(250)
      mediaRecorderRef.current = recorder
      startedAtRef.current = Date.now()
      setElapsedMs(0)
      setState('recording')

      timerRef.current = window.setInterval(() => {
        setElapsedMs(Date.now() - startedAtRef.current)
      }, 200)

      maxTimerRef.current = window.setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          stop().catch(() => {})
        }
      }, MAX_TURN_MS)
    } catch (e: any) {
      const msg = e?.name === 'NotAllowedError'
        ? 'Permiso de micrófono denegado. Habilítalo para usar voz.'
        : 'No fue posible acceder al micrófono.'
      setError(msg)
      setState('error')
      finishIdle()
    }
  }

  function stop() {
    return new Promise<Blob>((resolve, reject) => {
      const recorder = mediaRecorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        reject(new Error('No hay una grabación activa para detener.'))
        return
      }

      setState('stopping')
      stopResolverRef.current = resolve
      stopRejecterRef.current = reject

      recorder.onstop = () => {
        try {
          const type = recorder.mimeType || 'audio/webm'
          const blob = new Blob(chunksRef.current, { type })
          finishIdle()
          setState('idle')
          stopResolverRef.current?.(blob)
        } catch (err: any) {
          setError('No se pudo construir el audio grabado.')
          setState('error')
          finishIdle()
          stopRejecterRef.current?.(err)
        } finally {
          stopResolverRef.current = null
          stopRejecterRef.current = null
        }
      }

      try {
        recorder.stop()
      } catch (err: any) {
        setError('Error al detener la grabación.')
        setState('error')
        finishIdle()
        reject(err)
      }
    })
  }

  function cancel() {
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
    finishIdle()
    setState('idle')
    setError('')
  }

  useEffect(() => {
    return () => {
      cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    state,
    error,
    elapsedMs,
    start,
    stop,
    cancel,
  }
}
