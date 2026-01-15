const KEY = 'natubot_kiosk_state_v1'

export function loadState() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export function saveState(next) {
  try { localStorage.setItem(KEY, JSON.stringify(next)) } catch {}
}

export function clearState() {
  try { localStorage.removeItem(KEY) } catch {}
}
