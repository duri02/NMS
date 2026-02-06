export function base64ToBlob(base64: string, mime = 'audio/wav'): Blob {
  const clean = base64.includes(',') ? base64.split(',')[1] : base64
  const bin = atob(clean)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) {
    bytes[i] = bin.charCodeAt(i)
  }
  return new Blob([bytes], { type: mime })
}

export function blobToFile(blob: Blob, filename: string): File {
  return new File([blob], filename, { type: blob.type || 'application/octet-stream' })
}

export async function playAudioFromBlob(blob: Blob): Promise<void> {
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)

  const cleanup = () => {
    audio.onended = null
    audio.onerror = null
    URL.revokeObjectURL(url)
  }

  return new Promise((resolve, reject) => {
    audio.onended = () => {
      cleanup()
      resolve()
    }
    audio.onerror = () => {
      cleanup()
      reject(new Error('No fue posible reproducir el audio.'))
    }

    audio.play()
      .then(() => {
        // If playback starts, resolve immediately but keep cleanup on ended.
        resolve()
      })
      .catch((err) => {
        cleanup()
        reject(err)
      })
  })
}
