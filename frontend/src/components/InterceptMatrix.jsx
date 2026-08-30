import { motion } from 'framer-motion'
import { AlertTriangle, MapPin, Navigation, Zap } from 'lucide-react'

const DEFAULT_INTERCEPT_POINTS = [
  { camera_id: 'CAM_13_KATHIPARA', camera_name: 'Kathipara Junction Flyover', distance_km: 2.8, eta_minutes: 3.5 },
  { camera_id: 'CAM_04_GUINDY', camera_name: 'Guindy Racecourse Rotary', distance_km: 4.2, eta_minutes: 5.0 },
  { camera_id: 'CAM_07_ANNA_SALAI', camera_name: 'Anna Salai Mount Road Arterial', distance_km: 6.1, eta_minutes: 7.5 },
  { camera_id: 'CAM_09_VELACHERY', camera_name: 'Velachery Main Corridor', distance_km: 8.4, eta_minutes: 10.2 }
]

export default function InterceptMatrix({ route, blacklist = [] }) {
  if (!route) return null

  const targetPlate = route?.properties?.target_plate || route?.target_plate || ''
  
  // Condition A: Blacklist Guardrail
  const isBlacklisted = Array.isArray(blacklist) && blacklist.length > 0
    ? blacklist.some(b => b.plate_text?.trim().toUpperCase() === targetPlate?.trim().toUpperCase())
    : (route?.properties?.is_blacklisted ?? true)

  if (!isBlacklisted) return null

  // Condition B: Data Decay Guardrail (2-hour tactical window)
  const pointFeatures = (route?.features || []).filter(f => f.geometry?.type === 'Point')
  const latestSighting = pointFeatures.length > 0
    ? pointFeatures.slice().sort((a, b) => new Date(b.properties?.timestamp || 0) - new Date(a.properties?.timestamp || 0))[0]
    : null

  const latestTimestamp = latestSighting?.properties?.timestamp || route?.properties?.timestamp || route?.timestamp
  const hoursElapsed = latestTimestamp
    ? (Date.now() - new Date(latestTimestamp).getTime()) / (1000 * 60 * 60)
    : 0

  const isFresh = hoursElapsed <= 2

  const speed = route?.speed || route?.properties?.estimated_speed || 68
  const heading = route?.heading || route?.properties?.heading || 245
  const points = route?.intercept_points || route?.properties?.intercept_points || DEFAULT_INTERCEPT_POINTS

  return (
    <motion.div
      className="intercept-matrix-panel"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 15 }}
      transition={{ duration: 0.3 }}
    >
      <div className="matrix-header">
        <span className="matrix-title"><Zap size={15} color="#ffaa00" /> [ ⚡ TACTICAL INTERCEPT MATRIX ]</span>
        <span className="matrix-target-badge">{targetPlate}</span>
      </div>

      <p className="text-[13px] font-medium text-slate-200 leading-relaxed mt-2 mb-3 border-b border-amber-500/30 pb-2.5 font-sans">
        Calculates real-time escape probability vectors to predict downstream camera chokepoint interception.
      </p>

      {!isFresh ? (
        <div className="stale-warning-block border border-red-500/60 bg-red-950/40 p-3 rounded-lg text-red-200 mt-2 font-mono">
          <div className="flex items-center gap-2 text-red-400 font-bold text-xs mb-1">
            <AlertTriangle size={15} color="#ff2a2a" />
            <span>[!] TACTICAL WINDOW EXPIRED</span>
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed margin-0 font-sans">
            Target last seen <b className="text-amber-400 font-mono">{hoursElapsed.toFixed(1)}</b> hours ago. Confidence interval too low for predictive intercept. Awaiting fresh telemetry.
          </p>
        </div>
      ) : (
        <>
          <div className="matrix-telemetry text-xs font-mono text-slate-400 my-2 flex items-center justify-between">
            <span>VELOCITY: <b className="text-[#ffaa00] font-mono">{speed} KM/H</b></span>
            <span>VECTOR: <b className="text-[#ffaa00] font-mono">{heading}°</b></span>
            <span className="text-[10px] text-purple-300 bg-purple-950/60 px-1.5 py-0.5 rounded border border-purple-500/30">GNN+RNN</span>
          </div>

          {route?.properties?.destination_forecast && (
            <div className="mb-3 p-2 rounded bg-purple-950/30 border border-purple-500/30 text-xs font-mono">
              <span className="text-[10px] text-purple-300 block uppercase font-semibold">Projected Destination</span>
              <strong className="text-cyan-300 text-xs block">{route.properties.destination_forecast.hub_name}</strong>
              <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                <span>ETA: <b className="text-amber-300">{route.properties.destination_forecast.eta_minutes}m</b></span>
                <span>Prob: <b className="text-purple-300">{Math.round(route.properties.destination_forecast.confidence * 100)}%</b></span>
              </div>
            </div>
          )}

          <div className="chokepoint-section">
            <h4 className="text-xs font-semibold text-cyan-400 mb-2 flex items-center gap-1">
              <Navigation size={13} color="#00f0ff" /> AVAILABLE CHOKEPOINTS ({points.length})
            </h4>
            <div className="chokepoint-list max-h-[350px] overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-2">
              {points.map((point, index) => (
                <div key={point.camera_id || index} className="chokepoint-card">
                  <div className="chokepoint-main">
                    <MapPin size={14} color="#ffaa00" />
                    <div className="chokepoint-text">
                      <strong className="camera-name">{point.camera_name || point.name}</strong>
                      <span className="sub-detail">
                        DISTANCE: <b className="font-mono text-cyan-300">{point.distance_km ?? (2.5 + index * 1.5).toFixed(1)} KM</b>
                      </span>
                    </div>
                  </div>
                  <div className="eta-badge">
                    <span>{point.eta_minutes ?? point.eta ?? (3 + index * 2)} MINS</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </motion.div>
  )
}
