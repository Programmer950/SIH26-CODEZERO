import { useEffect, useState } from 'react'
import { Cpu, Flame, Radar, ShieldAlert } from 'lucide-react'
const count = value => value == null ? '—' : Intl.NumberFormat('en-IN').format(value)
export default function Header({ tab, setTab, overview, systemOnline, onSimulate, simulating }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => { const timer = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(timer) }, [])
  const metrics = [['NODES', overview?.active_cameras], ['SIGHTINGS / 24H', overview?.detections_24h], ['WATCHLIST', overview?.active_watchlist_count]]
  return <header className="sentinel-header"><div className="sentinel-brand"><Radar/><div><strong>URBAN SENTINEL</strong><small>CHENNAI GRID // ANPR COMMAND</small></div></div><nav className="header-tabs">{[['trace', Radar, 'Trajectory Trace'], ['heat', Flame, 'Macro Heatmap'], ['watch', ShieldAlert, 'Watchlist']].map(([id, Icon, label])=><button className={tab === id ? 'selected' : ''} onClick={()=>setTab(id)} key={id}><Icon size={14}/>{label}</button>)}</nav><div className="header-system"><div className="header-kpis">{metrics.map(([label,value])=><span key={label}><small>{label}</small><b>{count(value)}</b></span>)}</div><div className="status-clock"><i className={systemOnline ? 'live-blip' : 'dead-blip'}/><span>{systemOnline?'SYSTEM ONLINE':'RECONNECTING'}</span><time>{now.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}</time></div><button onClick={onSimulate} disabled={simulating} className="simulate"><Cpu size={14}/>{simulating ? 'SENDING' : 'SIM ALERT'}</button></div></header>
}
