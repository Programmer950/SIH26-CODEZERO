import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Route, Search, ScanSearch } from 'lucide-react'
import Panel from './Panel'
import { api } from '../lib/api'
import { useApi } from '../hooks/useApi'
const list = value => Array.isArray(value) ? value : value?.items || value?.suggestions || []
export default function TrajectoryPanel({ onTrajectory, onEvidence }) {
  const [plate, setPlate] = useState(''); const [suggestions, setSuggestions] = useState([])
  const { data, loading, execute } = useApi(api.trajectory, { immediate: false })
  useEffect(() => { const id = setTimeout(() => plate.length > 1 && api.suggestions(plate).then(x => setSuggestions(list(x))).catch(() => {}), 180); return () => clearTimeout(id) }, [plate])
  const search = async (value = plate) => { setPlate(value); setSuggestions([]); try { onTrajectory(await execute(value)) } catch {} }
  const steps = data?.features || []
  const avgSpeed = data?.properties?.total_trip_avg_speed_kmh ?? data?.total_trip_avg_speed_kmh
  return <Panel title="Trajectory Tracer" icon={Route} className="left-panel">
    <form className="search-box" onSubmit={e => { e.preventDefault(); search() }}><Search size={16}/><input value={plate} onChange={e => setPlate(e.target.value.toUpperCase())} placeholder="SEARCH PLATE / OCR"/><button>TRACE</button></form>
    {suggestions.length > 0 && <div className="suggestions">{suggestions.slice(0, 5).map((s, i) => { const text = typeof s === 'string' ? s : s.plate_text || s.plate || s.value; return <button key={i} onClick={() => search(text)}>{text}</button> })}</div>}
    <div className="trace-status flex items-center justify-between">
      <div className="flex items-center gap-1.5">
        <span className={loading ? 'pulse-dot amber' : 'pulse-dot'}></span>
        {loading ? 'RECONSTRUCTING SIGNAL PATH' : `${steps.length} GEO-SPATIAL EVENTS`}
      </div>
      {data && (
        <div className="text-right">
          <span className="text-[10px] font-mono text-slate-400 uppercase">AVG SPEED: </span>
          <span className="text-[#00f0ff] font-mono text-xs font-bold">
            {avgSpeed != null && Number(avgSpeed) > 0 ? `${Number(avgSpeed).toFixed(1)} km/h` : 'N/A'}
          </span>
        </div>
      )}
    </div>
    <div className="trace-list">{steps.filter(f => f.geometry?.type === 'Point' || !f.geometry).slice(0, 7).map((f, i) => { 
      const dist = Number(f.properties?.distance_from_prev_km || 0);
      const speed = f.properties?.segment_speed_kmh != null ? Number(f.properties.segment_speed_kmh) : null;
      return <motion.div initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .06 }} className="trace-event" key={i}>
        <i>{String(i + 1).padStart(2, '0')}</i>
        <div>
          <b>{f.properties?.camera_name || f.properties?.camera_id || 'ANPR NODE'}</b>
          <small>{f.properties?.timestamp || f.properties?.detected_at || 'TIMESTAMP UNAVAILABLE'}</small>
          {dist > 0 && (
            <div className="flex items-center gap-2 text-xs mt-1">
              <span className="text-amber-400 font-mono">+ {dist.toFixed(2)} km</span>
              <span className="text-gray-500">•</span>
              <span className="text-cyan-400 font-mono">⚡ {speed != null && speed > 0 ? `${speed.toFixed(1)} km/h` : '--'}</span>
            </div>
          )}
        </div>
      </motion.div> 
    })}</div>
    {data && <button className="primary-action" onClick={() => onEvidence(plate, steps)}><ScanSearch size={15}/> OPEN EVIDENCE INSPECTOR</button>}
  </Panel>
}
