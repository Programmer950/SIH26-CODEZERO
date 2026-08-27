import { useCallback, useEffect, useState } from 'react'
export function useApi(request, { immediate = true, interval } = {}) {
  const [data, setData] = useState(null); const [loading, setLoading] = useState(immediate); const [error, setError] = useState(null)
  const execute = useCallback(async (...args) => { setLoading(true); setError(null); try { const result = await request(...args); setData(result); return result } catch (e) { setError(e); throw e } finally { setLoading(false) } }, [request])
  useEffect(() => { if (!immediate) return; execute().catch(() => {}); if (!interval) return; const id = setInterval(() => execute().catch(() => {}), interval); return () => clearInterval(id) }, [execute, immediate, interval])
  return { data, loading, error, execute, setData }
}
export function useWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null); const [connected, setConnected] = useState(false)
  useEffect(() => { let socket; let timer; let alive = true
    const connect = () => { if (!alive) return; socket = new WebSocket(url); socket.onopen = () => setConnected(true); socket.onmessage = e => { try { setLastMessage(JSON.parse(e.data)) } catch { setLastMessage({ message: e.data }) } }; socket.onclose = () => { setConnected(false); if (alive) timer = setTimeout(connect, 3000) }; socket.onerror = () => socket.close() }
    connect(); return () => { alive = false; clearTimeout(timer); socket?.close() }
  }, [url]); return { lastMessage, connected, clearMessage: () => setLastMessage(null) }
}
