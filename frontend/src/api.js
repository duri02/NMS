export function makeApiClient(runtimeConfig) {
  const base = (runtimeConfig.apiBaseUrl || '').replace(/\/$/, '')

  function headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra }
    if (runtimeConfig.deviceId) h['X-Device-Id'] = runtimeConfig.deviceId
    if (runtimeConfig.kioskToken) h['X-Kiosk-Token'] = runtimeConfig.kioskToken
    return h
  }

  async function get(path) {
    const r = await fetch(base + path, { method: 'GET', headers: headers(), cache: 'no-store' })
    const j = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(j?.error || j?.detail || `HTTP ${r.status}`)
    return j
  }

  async function post(path, body) {
    const r = await fetch(base + path, { method: 'POST', headers: headers(), body: JSON.stringify(body) })
    const j = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(j?.error || j?.detail || `HTTP ${r.status}`)
    return j
  }

  return { get, post }
}
