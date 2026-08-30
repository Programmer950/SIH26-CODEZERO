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
  getTrajectory: async (plate, startTime, endTime) => {
    const start = startTime || new Date(Date.now() - 48 * 3600 * 1000).toISOString()
    const end = endTime || new Date(Date.now() + 24 * 3600 * 1000).toISOString()
    const trajPromise = request(`/api/v1/vehicles/${encodeURIComponent(plate)}/trajectory?${new URLSearchParams({ start_time: start, end_time: end })}`)
    const predPromise = request(`/api/v1/tracking/predict/${encodeURIComponent(plate)}`).catch(() => null)
    const [traj, pred] = await Promise.all([trajPromise, predPromise])
    if (traj && pred) {
      traj.prediction_status = pred.prediction_status || 'success'
      traj.prediction_message = pred.message
      traj.message = pred.message
      traj.predictive = pred
      if (pred.current_camera) traj.current_camera = pred.current_camera
      if (pred.probability_zone) traj.probability_zone = pred.probability_zone
      if (pred.probabilistic_nodes) {
        traj.probabilistic_nodes = pred.probabilistic_nodes
        if (traj.properties) traj.properties.probabilistic_nodes = pred.probabilistic_nodes
      }
      if (pred.cone_polygon) traj.cone_polygon = pred.cone_polygon
      if (pred.intercept_points) traj.intercept_points = pred.intercept_points
      if (pred.estimated_speed_kmh) traj.speed = pred.estimated_speed_kmh
      if (pred.current_heading !== undefined) traj.heading = pred.current_heading
      if (traj.properties) {
        traj.properties.current_camera = pred.current_camera
        traj.properties.probability_zone = pred.probability_zone
        traj.properties.prediction_status = pred.prediction_status || 'success'
        traj.properties.prediction_message = pred.message
        traj.properties.message = pred.message
      }
    }
    if (traj) {
      traj.total_trip_avg_speed_kmh = traj.total_trip_avg_speed_kmh ?? traj.properties?.total_trip_avg_speed_kmh
    }
    return traj
  },
  predict: plate => request(`/api/v1/tracking/predict/${encodeURIComponent(plate)}`),
  getVehicles: (params = {}) => {
    const q = new URLSearchParams()
    if (params.search) q.append('search', params.search)
    if (params.vehicle_class && params.vehicle_class !== 'all') q.append('vehicle_class', params.vehicle_class)
    if (params.is_watchlist !== undefined && params.is_watchlist !== null && params.is_watchlist !== '') q.append('is_watchlist', params.is_watchlist)
    if (params.limit) q.append('limit', params.limit)
    if (params.offset) q.append('offset', params.offset)
    const qs = q.toString() ? `?${q.toString()}` : ''
    return request(`/api/v1/vehicles${qs}`)
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

export default client
