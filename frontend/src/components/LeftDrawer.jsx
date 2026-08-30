import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Car, Crosshair, Flame, RefreshCw, Route, Search, ShieldAlert, Trash2, XCircle } from 'lucide-react'
import { client } from '../api/client'

const sightings = route => (route?.features || []).filter(feature => feature.geometry?.type === 'Point').sort((a,b)=>new Date(a.properties.timestamp)-new Date(b.properties.timestamp))
export default function LeftDrawer({ tab, setTab, route, tracePlate, onTracePlateChange, heatNodes, corridors, blacklist, onTrace, onStopTracking, onAdd, onDelete, loading }) {
  const [blacklistPlate, setBlacklistPlate] = useState(''); 
  const [reason, setReason] = useState('Stolen'); 
  const entries = useMemo(()=>sightings(route),[route]); 
  const target = route?.properties?.target_plate
  const avgSpeed = route?.properties?.total_trip_avg_speed_kmh ?? route?.total_trip_avg_speed_kmh

  // Fleet View State
  const [fleetSearch, setFleetSearch] = useState('')
  const [fleetFilter, setFleetFilter] = useState('all')
  const [fleetVehicles, setFleetVehicles] = useState([])
  const [fleetTotal, setFleetTotal] = useState(0)
  const [fleetLoading, setFleetLoading] = useState(false)

  const fetchFleet = useCallback(async () => {
    if (tab !== 'fleet') return
    setFleetLoading(true)
    try {
      const res = await client.getVehicles({
        search: fleetSearch.trim() || undefined,
        vehicle_class: fleetFilter !== 'watchlist' && fleetFilter !== 'all' ? fleetFilter : undefined,
        is_watchlist: fleetFilter === 'watchlist' ? true : undefined,
        limit: 150
      })
      if (res) {
        setFleetVehicles(res.vehicles || [])
        setFleetTotal(res.total_vehicles || 0)
      }
    } catch (err) {
      console.error('Failed to fetch fleet:', err)
    } finally {
      setFleetLoading(false)
    }
  }, [tab, fleetSearch, fleetFilter])

  useEffect(() => {
    if (tab === 'fleet') {
      fetchFleet()
      const timer = setInterval(fetchFleet, 6000)
      return () => clearInterval(timer)
    }
  }, [tab, fetchFleet])

  return <motion.aside key={tab} className="left-drawer h-[calc(100vh-2rem)] overflow-y-auto pb-24 flex flex-col custom-scrollbar" initial={{x:-36,opacity:0}} animate={{x:0,opacity:1}} exit={{x:-36,opacity:0}} transition={{type:'spring',stiffness:230,damping:27}}>
   {tab==='trace'&&<>
     <div className="drawer-heading"><Route/> TRAJECTORY TRACE</div>
     <form className="plate-search" onSubmit={event=>{event.preventDefault();onTrace(tracePlate)}}>
       <Search size={16}/>
       <input aria-label="Vehicle plate" value={tracePlate} onChange={event=>onTracePlateChange(event.target.value.toUpperCase())} placeholder="TN09AB1234"/>
       <button className="trace-button"><Crosshair size={13}/>TRACE</button>
       <button type="button" className="clear-trace" aria-label="Stop tracking" onClick={onStopTracking}><XCircle size={16}/></button>
     </form>
     {loading&&<div className="drawer-note">RECONSTRUCTING TELEMETRY…</div>}
     {route&&(
       <div className="route-summary mb-2">
         <div className="flex items-center justify-between">
           <div>
             <span>TARGET</span>
             <b>{target}</b>
           </div>
           <div className="text-right">
             <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">AVG CRUISE SPEED</span>
             <span className="text-[#00f0ff] font-mono text-sm font-bold">
               {avgSpeed != null && Number(avgSpeed) > 0 ? `${Number(avgSpeed).toFixed(1)} km/h` : 'N/A'}
             </span>
           </div>
         </div>
         <div className="flex items-center justify-between text-xs mt-1 text-slate-300">
           <small>{route.properties?.total_sightings ?? entries.length} corroborated sightings</small>
           {(route.properties?.blind_spots_recovered > 0 || route.blind_spots_recovered > 0) && (
             <span className="text-cyan-300 font-mono text-[10px] bg-cyan-950/60 border border-cyan-500/40 px-1.5 py-0.5 rounded">
               🕶️ {route.properties?.blind_spots_recovered || route.blind_spots_recovered} Blind Zone(s) Solved
             </span>
           )}
         </div>

         {/* Top Forecast Indicator */}
         {(route.forecast?.predictions?.[0] || route.properties?.forecast?.predictions?.[0]) && (
           <div className="mt-2 pt-2 border-t border-purple-500/30 text-xs font-mono">
             <div className="text-purple-400 text-[10px] font-bold uppercase tracking-wider">
               🔮 AI PREDICTED DESTINATION (WHERE NEXT?)
             </div>
             <div className="text-white font-semibold text-xs mt-0.5 flex items-center justify-between">
               <span>{(route.forecast?.predictions?.[0] || route.properties?.forecast?.predictions?.[0]).name}</span>
               <span className="text-pink-400 font-bold">
                 {(route.forecast?.predictions?.[0] || route.properties?.forecast?.predictions?.[0]).probability_percent}%
               </span>
             </div>
             <div className="text-slate-400 text-[10px] mt-0.5">
               ETA: <b className="text-amber-300">{(route.forecast?.predictions?.[0] || route.properties?.forecast?.predictions?.[0]).eta_minutes} min</b> · Dist: <b className="text-cyan-300">{(route.forecast?.predictions?.[0] || route.properties?.forecast?.predictions?.[0]).distance_km} km</b>
             </div>
           </div>
         )}
       </div>
     )}
     <div className="sighting-timeline flex-1 overflow-y-auto pr-2 custom-scrollbar">
       {entries.map((feature,index)=>{
         const event=feature.properties;
         const recovered=event.detected_plate!==target;
         const dist=Number(event.distance_from_prev_km||0);
         const speed=event.segment_speed_kmh != null ? Number(event.segment_speed_kmh) : null;
         return (
           <motion.article initial={{opacity:0,x:-14}} animate={{opacity:1,x:0}} transition={{delay:index*.08}} key={event.event_id} className={`sighting-card ${recovered?'recovered':''}`}>
             <i>{String(index+1).padStart(2,'0')}</i>
             <div>
               <b>{event.camera_name}</b>
               <small>{new Date(event.timestamp).toLocaleString('en-IN')}</small>
               <div className="flex items-center gap-2 mt-0.5">
                 <strong>{event.detected_plate}</strong>
               </div>
               {dist > 0 && (
                 <div className="flex items-center gap-2 text-xs mt-1">
                   <span className="text-amber-400 font-mono">+ {dist.toFixed(2)} km</span>
                   <span className="text-gray-500">•</span>
                   <span className="text-cyan-400 font-mono">⚡ {speed != null && speed > 0 ? `${speed.toFixed(1)} km/h` : '--'}</span>
                   {dist > 2.5 && (
                     <span className="text-purple-400 font-mono text-[10px] ml-auto">🕶️ GIS Bridge</span>
                   )}
                 </div>
               )}
             </div>
             <span>{Math.round(event.ocr_confidence*100)}%</span>
           </motion.article>
         )
       })}
       {!loading&&!entries.length&&<div className="drawer-empty">ENTER A PLATE TO RECONSTRUCT ITS PATH</div>}
     </div>
   </>}

   {tab==='fleet'&&<>
     <div className="drawer-heading flex items-center justify-between">
       <div className="flex items-center gap-2">
         <Car size={16} />
         <span>ALL SYSTEM VEHICLES</span>
       </div>
       <button
         type="button"
         onClick={fetchFleet}
         className="p-1 rounded-md text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition"
         title="Refresh Fleet"
       >
         <RefreshCw size={13} className={fleetLoading ? 'animate-spin' : ''} />
       </button>
     </div>
     <p className="drawer-intro">Live catalog of all unique vehicles tracked across Chennai ANPR grid.</p>

     <div className="plate-search mb-2">
       <Search size={16} />
       <input
         aria-label="Filter fleet by registration"
         value={fleetSearch}
         onChange={e => setFleetSearch(e.target.value.toUpperCase())}
         placeholder="FILTER BY PLATE (e.g. TN09)"
       />
       {fleetSearch && (
         <button type="button" className="clear-trace" onClick={() => setFleetSearch('')}>
           <XCircle size={16} />
         </button>
       )}
     </div>

     <div className="flex flex-wrap gap-1 mb-2.5">
       {[
         { id: 'all', label: 'All' },
         { id: 'watchlist', label: '🚨 Watchlist' },
         { id: 'SUV', label: 'SUV' },
         { id: 'Sedan', label: 'Sedan' },
         { id: 'Motorcycle', label: 'Bike' },
         { id: 'Auto-Rickshaw', label: 'Auto' },
         { id: 'Commercial Truck', label: 'Truck' },
       ].map(chip => (
         <button
           key={chip.id}
           type="button"
           onClick={() => setFleetFilter(chip.id)}
           className={`text-[10px] px-2 py-0.5 rounded-full border transition ${
             fleetFilter === chip.id
               ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-semibold shadow-[0_0_8px_rgba(0,240,255,0.3)]'
               : 'bg-slate-900/60 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'
           }`}
         >
           {chip.label}
         </button>
       ))}
     </div>

     <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono px-1 mb-2">
       <span>{fleetTotal} UNIQUE VEHICLES</span>
       {fleetLoading && <span className="text-cyan-400 animate-pulse text-[10px]">UPDATING...</span>}
     </div>

     <div className="sighting-timeline flex-1 overflow-y-auto pr-2 custom-scrollbar">
       {fleetVehicles.map((veh, idx) => (
         <motion.article
           initial={{ opacity: 0, x: -10 }}
           animate={{ opacity: 1, x: 0 }}
           transition={{ delay: Math.min(idx * 0.03, 0.3) }}
           key={veh.plate_text}
           className={`sighting-card mb-2 cursor-pointer transition-all hover:border-cyan-400/70 hover:shadow-[0_0_15px_rgba(0,240,255,0.15)] ${
             veh.is_watchlist ? 'recovered border-red-500/60' : ''
           }`}
           onClick={() => {
             onTracePlateChange(veh.plate_text)
             onTrace(veh.plate_text)
             if (setTab) setTab('trace')
           }}
         >
           <i>{String(idx + 1).padStart(2, '0')}</i>
           <div className="flex-1 min-w-0">
             <div className="flex items-center justify-between">
               <strong className="text-cyan-300 text-sm font-bold tracking-wide">{veh.plate_text}</strong>
               <span className="text-[9px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700">
                 {veh.vehicle_class || 'Vehicle'} · {veh.vehicle_color || 'Unknown'}
               </span>
             </div>

             {veh.is_watchlist && (
               <div className="flex items-center gap-1 text-[11px] text-red-400 font-semibold mt-1">
                 <ShieldAlert size={12} className="shrink-0 text-red-400 animate-pulse" />
                 <span className="truncate">WATCHLIST: {veh.watchlist_reason || 'Target Alert'}</span>
               </div>
             )}

             <div className="text-[11px] text-slate-300 mt-1 flex items-center justify-between">
               <span className="truncate">📍 {veh.last_camera_name || veh.last_camera_id || 'Grid Node'}</span>
               <span className="text-amber-400/90 font-mono shrink-0 ml-1">🎯 {veh.total_sightings} hits</span>
             </div>

             <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1 pt-1 border-t border-slate-800/60">
               <span>Last: {new Date(veh.last_seen).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
               <span className="text-cyan-400 font-bold hover:underline flex items-center gap-0.5">
                 TRACE PATH ⚡
               </span>
             </div>
           </div>
         </motion.article>
       ))}

       {!fleetLoading && fleetVehicles.length === 0 && (
         <div className="drawer-empty text-center py-8 text-slate-500 text-xs font-mono">
           NO VEHICLES FOUND IN GRID
         </div>
       )}
     </div>
   </>}

   {tab==='heat'&&<><div className="drawer-heading"><Flame/> MACRO HEATMAP</div><p className="drawer-intro">Live congestion rank and origin-destination corridor intelligence.</p><h4>CONGESTED INTERSECTIONS</h4><div className="rank-list custom-scrollbar">{heatNodes.slice().sort((a,b)=>b.vehicles_per_minute-a.vehicles_per_minute).map((node,index)=><article key={node.camera_id}><i>0{index+1}</i><div><b>{node.name}</b><small>{node.camera_id} · {node.congestion_intensity}</small></div><strong>{node.vehicles_per_minute}<small>/min</small></strong></article>)}</div><h4>TOP CORRIDORS</h4><div className="corridor-list custom-scrollbar">{corridors.map(c=><article key={`${c.origin_name}-${c.destination_name}`}><span>{c.origin_name} <b>→</b> {c.destination_name}</span><small>{c.total_trips} trips · {c.avg_duration_minutes} min avg</small></article>)}</div></>}
   {tab==='watch'&&<><div className="drawer-heading"><ShieldAlert/> WATCHLIST MANAGER</div><form className="blacklist-form" onSubmit={event=>{event.preventDefault();onAdd({plate_text:blacklistPlate,reason,alert_priority:'CRITICAL'});setBlacklistPlate('')}}><input aria-label="Blacklist plate" value={blacklistPlate} onChange={event=>onBlacklistPlateChange ? onBlacklistPlateChange(event.target.value.toUpperCase()) : setBlacklistPlate(event.target.value.toUpperCase())} placeholder="REGISTRATION"/><select value={reason} onChange={event=>setReason(event.target.value)}><option>Stolen</option><option>Wanted</option><option>Investigation</option></select><button>ADD TO WATCHLIST</button></form><div className="watch-entries custom-scrollbar">{blacklist.map(item=><article key={item.plate_text}><ShieldAlert size={15}/><div><b>{item.plate_text}</b><small>{item.reason} · {item.alert_priority}</small></div><button onClick={()=>onDelete(item.plate_text)} aria-label={`Delete ${item.plate_text}`}><Trash2 size={15}/></button></article>)}{!blacklist.length&&<div className="drawer-empty">NO ACTIVE WATCHLIST ENTRIES</div>}</div></>}
  </motion.aside>
}
