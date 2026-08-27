import { useCallback, useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const request = async (path, options = {}) => {
  const response = await fetch(`${API_URL}${path}`, { headers: { 'Content-Type': 'application/json', ...options.headers }, ...options })
  if (!response.ok) throw new Error(`Request failed (${response.status})`)
  return response.status === 204 ? null : response.json()
}

export const client = {
  overview: () => request('/api/v1/analytics/overview'),
  cameras: () => request('/api/v1/cameras'),
  heatmap: () => request('/api/v1/analytics/heatmap'),
  odMatrix: () => request('/api/v1/analytics/od-matrix'),
  blacklist: () => request('/api/v1/blacklist'),
  addBlacklist: payload => request('/api/v1/blacklist', { method: 'POST', body: JSON.stringify(payload) }),
  deleteBlacklist: plate => request(`/api/v1/blacklist/${encodeURIComponent(plate)}`, { method: 'DELETE' }),
  getTrajectory: (plate, startTime, endTime) => {
    const start = startTime || new Date(Date.now() - 48 * 3600 * 1000).toISOString()
    const end = endTime || new Date(Date.now() + 24 * 3600 * 1000).toISOString()
    return request(`/api/v1/vehicles/${encodeURIComponent(plate)}/trajectory?${new URLSearchParams({ start_time: start, end_time: end })}`)
  },
  matchCheck: (sourceEvent, targetEvent) => request('/api/v1/vehicles/match-check', { method: 'POST', body: JSON.stringify({ source_event: sourceEvent, target_event: targetEvent }) }),
  triggerDemoAlert: async payload => {
    const res = await fetch(`${API_URL}/api/v1/events`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (!res.ok) throw new Error('Failed to trigger alert')
    return res.json()
  },
}

export function useEndpoint(getter, delay = 15000) {
  const [data, setData] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState(null)
  const refresh = useCallback(async () => { setLoading(true); try { const next = await getter(); setData(next); setError(null); return next } catch (issue) { setError(issue); return null } finally { setLoading(false) } }, [getter])
  useEffect(() => { refresh(); const id = setInterval(refresh, delay); return () => clearInterval(id) }, [refresh, delay])
  return { data, loading, error, refresh }
}

export function useAlertSocket() {
  const [alert, setAlert] = useState(null); const [online, setOnline] = useState(false)
  useEffect(() => { let socket; let retry; let active = true
    const connect = () => { socket = new WebSocket(`${API_URL.replace(/^http/, 'ws')}/ws/alerts`); socket.onopen = () => setOnline(true); socket.onmessage = event => { try { setAlert(JSON.parse(event.data)) } catch { /* Ignore malformed telemetry */ } }; socket.onclose = () => { setOnline(false); if (active) retry = setTimeout(connect, 3000) } }
    connect(); return () => { active = false; clearTimeout(retry); socket?.close() }
  }, [])
  return { alert, online, dismiss: () => setAlert(null) }
}
