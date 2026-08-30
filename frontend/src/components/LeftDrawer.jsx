import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Compass, Crosshair, Flame, MapPin, Navigation, Route, Search, ShieldAlert, Sparkles, Trash2, XCircle, Zap } from 'lucide-react'

const sightings = route => (route?.features || [])
  .filter(feature => feature.geometry?.type === 'Point' && !feature.properties?.is_forecast_intersection)
  .sort((a, b) => new Date(a.properties.timestamp) - new Date(b.properties.timestamp))

export default function LeftDrawer({
  tab,
  route,
  tracePlate,
  onTracePlateChange,
  heatNodes,
  corridors,
  blacklist,
  onTrace,
  onStopTracking,
  onAdd,
  onDelete,
  loading
}) {
  const [blacklistPlate, setBlacklistPlate] = useState('')
  const [reason, setReason] = useState('Stolen')
  const entries = useMemo(() => sightings(route), [route])
  const target = route?.properties?.target_plate

  // Predictive & Blind-Spot Data
  const predictions = route?.properties?.predictions || {}
  const nextIntersections = predictions.next_intersections || route?.properties?.intercept_points || []
  const destinationForecast = predictions.destination_forecast || route?.properties?.destination_forecast
  const blindSpotAnalysis = route?.properties?.blind_spot_analysis || {}
  const hasBlindSpots = blindSpotAnalysis.has_blind_spots

  return (
    <motion.aside
      key={tab}
      className="left-drawer h-[calc(100vh-2rem)] overflow-y-auto pb-24 flex flex-col custom-scrollbar"
      initial={{ x: -36, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -36, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 230, damping: 27 }}
    >
      {tab === 'trace' && (
        <>
          <div className="drawer-heading">
            <Route /> TRAJECTORY RECONSTRUCTION
          </div>

          <form className="plate-search" onSubmit={event => { event.preventDefault(); onTrace(tracePlate) }}>
            <Search size={16} />
            <input
              aria-label="Vehicle plate"
              value={tracePlate}
              onChange={event => onTracePlateChange(event.target.value.toUpperCase())}
              placeholder="TN09AB1234"
            />
            <button className="trace-button">
              <Crosshair size={13} /> TRACE
            </button>
            <button type="button" className="clear-trace" aria-label="Stop tracking" onClick={onStopTracking}>
              <XCircle size={16} />
            </button>
          </form>

          {loading && <div className="drawer-note">RECONSTRUCTING TELEMETRY & GIS ROAD NETWORK…</div>}

          {route && (
            <div className="route-summary">
              <span>TARGET</span>
              <b>{target}</b>
              <small>{route.properties?.total_sightings ?? entries.length} confirmed camera sightings</small>
            </div>
          )}

          {/* 1. GIS Blind-Spot Interpolation Summary Banner */}
          {route && hasBlindSpots && (
            <div className="mx-3 my-2 p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs font-mono">
              <div className="flex items-center gap-1.5 font-bold text-amber-400 mb-1">
                <Compass size={14} />
                <span>GIS BLIND-ZONE INTERPOLATION</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-tight">
                Vehicle traversed <b className="text-amber-300">{blindSpotAnalysis.total_blind_spots}</b> unmonitored blind zones ({blindSpotAnalysis.total_blind_distance_km} km). Curved route reconstructed via GIS road network topology.
              </p>
            </div>
          )}

          {/* 2. GNN / RNN Predictive Trajectory Forecasting Card (Where Next?) */}
          {route && nextIntersections.length > 0 && (
            <div className="mx-3 my-2 p-3 rounded-lg bg-purple-950/40 border border-purple-500/40 text-purple-200 text-xs font-mono">
              <div className="flex items-center justify-between font-bold text-purple-300 mb-2">
                <span className="flex items-center gap-1.5">
                  <Sparkles size={14} color="#e879f9" /> WHERE NEXT? (GNN/RNN FORECAST)
                </span>
                <span className="text-[10px] bg-purple-900/60 px-1.5 py-0.5 rounded text-purple-300 border border-purple-500/30">
                  {predictions.model_architecture || 'GNN_RNN'}
                </span>
              </div>

              {destinationForecast && (
                <div className="mb-2.5 p-2 rounded bg-slate-900/80 border border-purple-500/20">
                  <span className="text-[10px] text-slate-400 block uppercase tracking-wider">Projected Destination Hub</span>
                  <b className="text-cyan-300 text-xs block truncate">{destinationForecast.hub_name}</b>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                    <span>ETA: <b className="text-amber-300">{destinationForecast.eta_minutes} mins</b></span>
                    <span>Confidence: <b className="text-purple-300">{Math.round(destinationForecast.confidence * 100)}%</b></span>
                  </div>
                </div>
              )}

              <span className="text-[10px] text-slate-400 block mb-1 uppercase font-semibold">Predicted Next Intersections</span>
              <div className="space-y-1.5">
                {nextIntersections.slice(0, 3).map((item, idx) => (
                  <div key={item.camera_id || idx} className="p-1.5 rounded bg-slate-900/60 border border-slate-800 flex flex-col gap-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-slate-200 truncate max-w-[170px]">{item.camera_name || item.name}</span>
                      <b className="text-purple-300 font-mono">{item.confidence_pct || Math.round(item.probability * 100)}%</b>
                    </div>
                    {/* Probability Progress Bar */}
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-cyan-400 h-1.5 rounded-full"
                        style={{ width: `${Math.min(100, item.confidence_pct || (item.probability * 100))}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>{item.distance_km} km</span>
                      <span className="text-cyan-300">ETA {item.eta_minutes}m</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. Reconstructed Sightings Timeline */}
          <div className="sighting-timeline flex-1 overflow-y-auto pr-2 custom-scrollbar">
            {entries.map((feature, index) => {
              const event = feature.properties
              const recovered = event.detected_plate !== target
              return (
                <motion.article
                  initial={{ opacity: 0, x: -14 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.08 }}
                  key={event.event_id || index}
                  className={`sighting-card ${recovered ? 'recovered' : ''}`}
                >
                  <i>{String(index + 1).padStart(2, '0')}</i>
                  <div>
                    <b>{event.camera_name}</b>
                    <small>{new Date(event.timestamp).toLocaleString('en-IN')}</small>
                    <strong>{event.detected_plate}</strong>
                  </div>
                  <span>{Math.round(event.ocr_confidence * 100)}%</span>
                </motion.article>
              )
            })}
            {!loading && !entries.length && (
              <div className="drawer-empty">ENTER A PLATE TO RECONSTRUCT ITS PATH</div>
            )}
          </div>
        </>
      )}

      {tab === 'heat' && (
        <>
          <div className="drawer-heading">
            <Flame /> MACRO HEATMAP
          </div>
          <p className="drawer-intro">Live congestion rank and origin-destination corridor intelligence.</p>
          <h4>CONGESTED INTERSECTIONS</h4>
          <div className="rank-list custom-scrollbar">
            {heatNodes
              .slice()
              .sort((a, b) => b.vehicles_per_minute - a.vehicles_per_minute)
              .map((node, index) => (
                <article key={node.camera_id}>
                  <i>0{index + 1}</i>
                  <div>
                    <b>{node.name}</b>
                    <small>{node.camera_id} · {node.congestion_intensity}</small>
                  </div>
                  <strong>{node.vehicles_per_minute}<small>/min</small></strong>
                </article>
              ))}
          </div>
          <h4>TOP CORRIDORS</h4>
          <div className="corridor-list custom-scrollbar">
            {corridors.map(c => (
              <article key={`${c.origin_name}-${c.destination_name}`}>
                <span>{c.origin_name} <b>→</b> {c.destination_name}</span>
                <small>{c.total_trips} trips · {c.avg_duration_minutes} min avg</small>
              </article>
            ))}
          </div>
        </>
      )}

      {tab === 'watch' && (
        <>
          <div className="drawer-heading">
            <ShieldAlert /> WATCHLIST MANAGER
          </div>
          <form className="blacklist-form" onSubmit={event => {
            event.preventDefault()
            onAdd({ plate_text: blacklistPlate, reason, alert_priority: 'CRITICAL' })
            setBlacklistPlate('')
          }}>
            <input
              aria-label="Blacklist plate"
              value={blacklistPlate}
              onChange={event => setBlacklistPlate(event.target.value.toUpperCase())}
              placeholder="REGISTRATION"
            />
            <select value={reason} onChange={event => setReason(event.target.value)}>
              <option>Stolen</option>
              <option>Wanted</option>
              <option>Investigation</option>
            </select>
            <button>ADD TO WATCHLIST</button>
          </form>
          <div className="watch-entries custom-scrollbar">
            {blacklist.map(item => (
              <article key={item.plate_text}>
                <ShieldAlert size={15} />
                <div>
                  <b>{item.plate_text}</b>
                  <small>{item.reason} · {item.alert_priority}</small>
                </div>
                <button onClick={() => onDelete(item.plate_text)} aria-label={`Delete ${item.plate_text}`}>
                  <Trash2 size={15} />
                </button>
              </article>
            ))}
            {!blacklist.length && <div className="drawer-empty">NO ACTIVE WATCHLIST ENTRIES</div>}
          </div>
        </>
      )}
    </motion.aside>
  )
}
