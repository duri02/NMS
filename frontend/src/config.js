export const DEFAULTS = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  deviceId: import.meta.env.VITE_DEVICE_ID || '',
  kioskToken: import.meta.env.VITE_KIOSK_TOKEN || '',
}

export async function loadRuntimeConfig() {
  try {
    const res = await fetch('/kiosk-config.json', { cache: 'no-store' })
    if (!res.ok) return { ...DEFAULTS, source: 'env' }
    const cfg = await res.json()
    return {
      apiBaseUrl: cfg.apiBaseUrl || DEFAULTS.apiBaseUrl,
      deviceId: cfg.deviceId || DEFAULTS.deviceId,
      kioskToken: cfg.kioskToken || DEFAULTS.kioskToken,
      source: 'kiosk-config.json',
    }
  } catch {
    return { ...DEFAULTS, source: 'env' }
  }
}
