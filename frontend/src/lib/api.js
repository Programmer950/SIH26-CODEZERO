const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const json = async (path, options = {}) => {
  const response = await fetch(`${BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json', ...options.headers }, ...options })
  if (!response.ok) throw new Error(`${response.status}: ${await response.text() || response.statusText}`)
  if (response.status === 204) return null
  return response.json()
}
const query = (params = {}) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  return entries.length ? `?${new URLSearchParams(entries)}` : ''
}
export const api = {
  health: () => json('/'),
  overview: () => json('/api/v1/analytics/overview'),
  cameras: () => json('/api/v1/cameras'),
  upsertCamera: (data) => json('/api/v1/cameras', { method: 'POST', body: JSON.stringify(data) }),
  recentFeed: (id) => json(`/api/v1/cameras/${encodeURIComponent(id)}/recent-feed`),
  trajectory: (plate) => json(`/api/v1/vehicles/${encodeURIComponent(plate)}/trajectory`),
  suggestions: (value) => json(`/api/v1/vehicles/search-suggestions${query({ q: value, query: value })}`),
  matchCheck: (data) => json('/api/v1/vehicles/match-check', { method: 'POST', body: JSON.stringify(data) }),
  heatmap: () => json('/api/v1/analytics/heatmap'),
  alerts: () => json('/api/v1/alerts'),
  blacklist: () => json('/api/v1/blacklist'),
  addBlacklist: (data) => json('/api/v1/blacklist', { method: 'POST', body: JSON.stringify(data) }),
  removeBlacklist: (plate) => json(`/api/v1/blacklist/${encodeURIComponent(plate)}`, { method: 'DELETE' }),
  odMatrix: () => json('/api/v1/analytics/od-matrix'),
}
export const wsUrl = `${BASE_URL.replace(/^http/, 'ws')}/ws/alerts`
