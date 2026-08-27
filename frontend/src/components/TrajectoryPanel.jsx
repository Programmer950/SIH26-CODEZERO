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
  return <Panel title="Trajectory Tracer" icon={Route} className="left-panel">
    <form className="search-box" onSubmit={e => { e.preventDefault(); search() }}><Search size={16}/><input value={plate} onChange={e => setPlate(e.target.value.toUpperCase())} placeholder="SEARCH PLATE / OCR"/><button>TRACE</button></form>
    {suggestions.length > 0 && <div className="suggestions">{suggestions.slice(0, 5).map((s, i) => { const text = typeof s === 'string' ? s : s.plate_text || s.plate || s.value; return <button key={i} onClick={() => search(text)}>{text}</button> })}</div>}
    <div className="trace-status"><span className={loading ? 'pulse-dot amber' : 'pulse-dot'}></span>{loading ? 'RECONSTRUCTING SIGNAL PATH' : `${steps.length} GEO-SPATIAL EVENTS`}</div>
    <div className="trace-list">{steps.slice(0, 7).map((f, i) => <motion.div initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .06 }} className="trace-event" key={i}><i>{String(i + 1).padStart(2, '0')}</i><div><b>{f.properties?.camera_name || f.properties?.camera_id || 'ANPR NODE'}</b><small>{f.properties?.timestamp || f.properties?.detected_at || 'TIMESTAMP UNAVAILABLE'}</small></div></motion.div>)}</div>
    {data && <button className="primary-action" onClick={() => onEvidence(plate, steps)}><ScanSearch size={15}/> OPEN EVIDENCE INSPECTOR</button>}
  </Panel>
}
