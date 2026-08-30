import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Clock, Compass, Cpu, MapPin, Navigation, Percent, ShieldCheck, Zap } from 'lucide-react'
import client from '../api/client'

const getProbabilityMeta = (prob) => {
  const p = Number(prob ?? 0)
  if (p >= 0.5) {
    return { color: '#ff2a2a', label: 'HIGH THREAT', badgeClass: 'prob-badge-high' }
  }
  if (p >= 0.2) {
    return { color: '#ff9f0a', label: 'ELEVATED', badgeClass: 'prob-badge-med' }
  }
  return { color: '#00f0ff', label: 'PROBABLE', badgeClass: 'prob-badge-low' }
}

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
  const latestCameraId = latestSighting?.properties?.camera_id || route?.properties?.latest_camera_id || route?.current_camera || ''
  const trajectoryLength = pointFeatures.length
  const blindSpotsRecovered = route?.properties?.blind_spots_recovered || route?.blind_spots_recovered || 0

  const hoursElapsed = latestTimestamp
    ? (Date.now() - new Date(latestTimestamp).getTime()) / (1000 * 60 * 60)
    : 0

  const isFresh = hoursElapsed <= 2

  // Reactive state hook: Re-trigger prediction lookup whenever latest_camera_id or trajectory length changes
  const [predictionData, setPredictionData] = useState(null)

  useEffect(() => {
    if (!targetPlate) {
      setPredictionData(null)
      return
    }

    let isMounted = true
    client.predict(targetPlate)
      .then(res => {
        if (isMounted && res) {
          setPredictionData(res)
        }
      })
      .catch(err => {
        console.warn('Prediction query error:', err)
      })

    return () => {
      isMounted = false
    }
  }, [targetPlate, latestCameraId, trajectoryLength])

  const nodes = predictionData?.forecast?.predictions || predictionData?.probabilistic_nodes || route?.forecast?.predictions || route?.probabilistic_nodes || route?.properties?.probabilistic_nodes || []

  return (
    <motion.div
      className="intercept-matrix-panel"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 15 }}
      transition={{ duration: 0.3 }}
    >
      <div className="matrix-header">
        <span className="matrix-title flex items-center gap-1.5">
          <Cpu size={15} color="#ec4899" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400 font-bold">
            [ AI TRAJECTORY FORECASTER ]
          </span>
        </span>
        <span className="matrix-target-badge">{targetPlate}</span>
      </div>

      <p className="text-[12px] font-medium text-slate-300 leading-relaxed mt-2 mb-2 border-b border-purple-500/30 pb-2 font-sans">
        Hybrid <b>GNN + RNN Deep Sequence Model</b> forecasting downstream intersections, travel ETAs, and road network vectors.
      </p>

      {blindSpotsRecovered > 0 && (
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-500/40 px-2 py-1 rounded mb-2">
          <ShieldCheck size={13} className="text-cyan-400" />
          <span><b>{blindSpotsRecovered}</b> Blind-Spot Route(s) Recovered via GIS Constraints</span>
        </div>
      )}

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
      ) : nodes.length === 0 ? (
        <div className="empty-destinations-block p-4 rounded-lg bg-slate-900/60 border border-slate-700/60 text-slate-300 text-xs font-mono my-2 text-center">
          <div className="text-cyan-400 font-semibold mb-1 flex items-center justify-center gap-1.5">
            <Navigation size={13} color="#00f0ff" />
            <span>CURRENT NODE: {latestCameraId || 'LAST KNOWN'}</span>
          </div>
          <p className="text-slate-400 text-[11px] font-sans m-0">
            No downstream transitions recorded for this specific corridor in historical traffic data.
          </p>
        </div>
      ) : (
        <>
          <div className="matrix-telemetry text-xs font-mono text-slate-400 my-2 flex items-center justify-between">
            <span>MODEL: <b className="text-purple-400 font-mono">GNN + GRU</b></span>
            <span>DESTINATIONS: <b className="text-[#00f0ff] font-mono">{nodes.length}</b></span>
          </div>

          <div className="chokepoint-section">
            <h4 className="text-xs font-semibold text-purple-300 mb-2 flex items-center gap-1">
              <Compass size={13} color="#ec4899" /> PREDICTED NEXT INTERSECTIONS
            </h4>
            <div className="chokepoint-list max-h-[350px] overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-2">
              {nodes.map((node, index) => {
                const prob = Number(node.probability ?? 0)
                const percent = node.probability_percent || (prob * 100).toFixed(1)
                const wholePercent = Math.round(prob * 100)
                const meta = getProbabilityMeta(prob)
                const name = node.camera_name || node.name || node.camera_id || `Node ${index + 1}`
                const eta = node.eta_minutes || (node.distance_km ? (node.distance_km / 0.7).toFixed(1) : 3.0)
                const dist = node.distance_km ? Number(node.distance_km).toFixed(1) : null

                return (
                  <div key={node.camera_id || index} className="chokepoint-card border border-purple-500/20 bg-slate-900/80 hover:border-purple-500/50 transition">
                    <div className="chokepoint-main">
                      <MapPin size={16} color={meta.color} />
                      <div className="chokepoint-text flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <strong className="camera-name text-white font-medium text-xs">{name}</strong>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400 mt-0.5">
                          <span>NODE: <b className="text-cyan-300">{node.camera_id || node.next_camera || `DEST_${index + 1}`}</b></span>
                          {dist && <span>· <b>{dist} km</b></span>}
                          {eta && (
                            <span className="text-amber-300 flex items-center gap-0.5">
                              <Clock size={10} /> <b>{eta}m ETA</b>
                            </span>
                          )}
                        </div>
                        <div className="prob-bar-container mt-1.5">
                          <div
                            className="prob-bar-fill"
                            style={{
                              width: `${Math.min(100, Math.max(5, wholePercent))}%`,
                              background: `linear-gradient(90deg, ${meta.color}, #ec4899)`
                            }}
                          />
                        </div>
                      </div>
                    </div>
                    <div className={`prob-badge ${meta.badgeClass} ml-2 flex flex-col items-center justify-center`}>
                      <div className="flex items-center gap-0.5">
                        <Percent size={10} />
                        <span className="font-bold">{percent}%</span>
                      </div>
                      <span className="text-[8px] uppercase tracking-wider text-slate-300 mt-0.5">{meta.label}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </motion.div>
  )
}

