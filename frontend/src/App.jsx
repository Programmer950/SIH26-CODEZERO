import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import Header from './components/Header'
import SentinelMap from './components/SentinelMap'
import LeftDrawer from './components/LeftDrawer'
import AlertBanner from './components/AlertBanner'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import { client, useAlertSocket, useEndpoint } from './api/client'

import InterceptMatrix from './components/InterceptMatrix'

export default function App() {
  const [tab, setTab] = useState('trace')
  const [tracePlate, setTracePlate] = useState('')
  const [route, setRoute] = useState(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [simulating, setSimulating] = useState(false)

  const overview = useEndpoint(client.overview, 15000)
  const cameras = useEndpoint(client.cameras, 20000)
  const heatmap = useEndpoint(client.heatmap, 20000)
  const matrix = useEndpoint(client.odMatrix, 30000)
  const watchlist = useEndpoint(client.blacklist, 12000)
  const socket = useAlertSocket()

  useEffect(() => {
    const pollLiveTelemetry = () => {
      overview.refresh()
      heatmap.refresh()
    }
    const intervalId = setInterval(pollLiveTelemetry, 3000)
    return () => clearInterval(intervalId)
  }, [overview.refresh, heatmap.refresh])

  useEffect(() => {
    if (tab !== 'trace') {
      setRoute(null)
      setTracePlate('')
      setActiveTrackedPlate('')
    }
  }, [tab])

  const [activeTrackedPlate, setActiveTrackedPlate] = useState('')

  const trace = useCallback(async (plate, isSilent = false) => {
    const target = plate?.trim() || activeTrackedPlate?.trim()
    if (!target) return

    if (!isSilent) {
      setRoute(null)
      setRouteLoading(true)
    }

    try {
      const data = await client.getTrajectory(target)
      setRoute(data ? { ...data } : null)
      setActiveTrackedPlate(target)
    } catch {
      if (!isSilent) setRoute(null)
    } finally {
      if (!isSilent) setRouteLoading(false)
    }
  }, [activeTrackedPlate])

  // 5-second Silent Auto-Polling for Active Trajectory Trace & Escape Cone
  useEffect(() => {
    if (tab !== 'trace' || !activeTrackedPlate) return

    const intervalId = setInterval(() => {
      trace(activeTrackedPlate, true)
    }, 5000)

    return () => clearInterval(intervalId)
  }, [tab, activeTrackedPlate, trace])

  // Instant Trajectory Refresh on WebSocket Real-Time Alert Stream
  useEffect(() => {
    if (!socket.alert || tab !== 'trace' || !activeTrackedPlate) return
    const alertPlate = socket.alert.plate_text || socket.alert.detected_plate
    if (alertPlate && alertPlate.trim().toUpperCase() === activeTrackedPlate.trim().toUpperCase()) {
      trace(activeTrackedPlate, true)
    }
  }, [socket.alert, tab, activeTrackedPlate, trace])

  const stopTracking = useCallback(() => {
    setRoute(null)
    setTracePlate('')
    setActiveTrackedPlate('')
  }, [])

  const addBlacklist = useCallback(async entry => {
    if (!entry.plate_text.trim()) return
    await client.addBlacklist(entry)
    watchlist.refresh()
  }, [watchlist])

  const deleteBlacklist = useCallback(async plate => {
    await client.deleteBlacklist(plate)
    watchlist.refresh()
  }, [watchlist])

  const handleSimulateAlert = async () => {
    setSimulating(true)
    try {
      await client.triggerDemoAlert({
        camera_id: 'CAM_01_KOYAMBEDU_JN',
        plate_text: 'TN09AB9999',
        ocr_confidence: 0.98,
        timestamp: new Date().toISOString(),
        vehicle_class: 'SUV',
        vehicle_color: 'Black',
        embedding: [0.1, 0.2, 0.3]
      })
    } catch (err) {
      console.error('Simulation failed:', err)
    } finally {
      setSimulating(false)
    }
  }

  const cameraList = cameras.data?.cameras || []
  const heatNodes = heatmap.data?.nodes || []
  const corridors = matrix.data?.corridors || []
  const blacklist = Array.isArray(watchlist.data) ? watchlist.data : []

  return (
    <main className="sentinel-shell">
      <SentinelMap cameras={cameraList} route={route} heatNodes={heatNodes} odCorridors={corridors} activeTab={tab} blacklist={blacklist} />
      <div className="void-vignette" />
      <div className="crt-lines" />
      <Header tab={tab} setTab={setTab} overview={overview.data} systemOnline={socket.online} onSimulate={handleSimulateAlert} simulating={simulating} />
      <AnimatePresence mode="wait">
        {tab === 'analytics' ? (
          <AnalyticsDashboard key="analytics" />
        ) : (
          <LeftDrawer
            key={tab}
            tab={tab}
            setTab={setTab}
            route={route}
            tracePlate={tracePlate}
            onTracePlateChange={setTracePlate}
            heatNodes={heatNodes}
            corridors={corridors}
            blacklist={blacklist}
            onTrace={trace}
            onStopTracking={stopTracking}
            onAdd={addBlacklist}
            onDelete={deleteBlacklist}
            loading={routeLoading}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {tab === 'trace' && route && (
          <div className="absolute top-[108px] right-6 z-[1000] w-96 max-h-[calc(100vh-140px)] overflow-y-auto custom-scrollbar">
            <InterceptMatrix route={route} blacklist={blacklist} />
          </div>
        )}
      </AnimatePresence>
      <AlertBanner alert={socket.alert} onClose={socket.dismiss} />
      <footer className="map-readout">
        CHENNAI METROPOLITAN GRID <i /> ENCRYPTED TELEMETRY <i /> {cameraList.length} CAMERAS DISCOVERED
      </footer>
    </main>
  )
}
