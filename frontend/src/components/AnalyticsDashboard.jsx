import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, BarChart3, Car, AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  CartesianGrid,
  AreaChart,
  Area
} from 'recharts'

const DEFAULT_SUMMARY = {
  total_vehicles_24h: 14250,
  top_bottlenecks: [
    { camera: 'CAM_13_KATHIPARA_FLY', volume: 3210 },
    { camera: 'CAM_01_KOYAMBEDU_JN', volume: 2840 },
    { camera: 'CAM_04_GUINDY_ROUT', volume: 2410 },
    { camera: 'CAM_07_ANNA_SALAI', volume: 1950 },
    { camera: 'CAM_09_VELACHERY_MAIN', volume: 1620 }
  ],
  fleet_distribution: [
    { type: 'SUV', count: 6120 },
    { type: 'Sedan', count: 4820 },
    { type: 'Truck', count: 1910 },
    { type: 'Motorcycle', count: 1400 }
  ],
  telemetry_trend: [
    { time: '00:00', count: 850 },
    { time: '03:00', count: 420 },
    { time: '06:00', count: 1890 },
    { time: '09:00', count: 4320 },
    { time: '12:00', count: 3850 },
    { time: '15:00', count: 3410 },
    { time: '18:00', count: 5120 },
    { time: '21:00', count: 2100 }
  ]
}

const NEON_COLORS = ['#00e5ff', '#b000ff', '#ff0055', '#00ffcc', '#facc15']

export default function AnalyticsDashboard() {
  const [data, setData] = useState(DEFAULT_SUMMARY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/v1/analytics/summary')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (err) {
      console.warn('Backend endpoint offline, displaying cached grid telemetry:', err)
      setError('Live connection offline. Showing cached grid telemetry.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <motion.div
      className="analytics-overlay"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <div className="analytics-header">
        <div>
          <h2><BarChart3 size={22} color="#00f0ff" /> CITY EYE // TRAFFIC & BOTTLENECK ANALYTICS</h2>
          <p>Real-time ANPR Telemetry Aggregation & Grid Congestion Intelligence</p>
        </div>
        <button className="analytics-refresh-btn" onClick={fetchAnalytics} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          {loading ? 'SYNCING...' : 'REFRESH'}
        </button>
      </div>

      {error && (
        <div className="analytics-notice">
          <AlertTriangle size={15} color="#ffb000" />
          <span>{error}</span>
        </div>
      )}

      <div className="analytics-grid">
        {/* Metric Card 1: 24H Traffic Volume */}
        <div className="analytics-card glass-card">
          <div className="card-top">
            <span className="card-label"><Activity size={16} /> 24H TRAFFIC VOLUME</span>
            <span className="badge badge-cyan">LIVE</span>
          </div>
          <div className="card-big-stat">
            <strong>{Intl.NumberFormat('en-IN').format(data.total_vehicles_24h || 0)}</strong>
            <small>VEHICLES DETECTED</small>
          </div>
          <div className="card-foot">
            <TrendingUp size={14} color="#47ff9e" />
            <span>+14.2% vs previous 24-hour baseline</span>
          </div>
        </div>

        {/* Metric Card 2: Top Bottlenecks (Horizontal Bar Chart) */}
        <div className="analytics-card glass-card span-col-2">
          <div className="card-top">
            <span className="card-label"><AlertTriangle size={16} color="#ff2a2a" /> TOP BOTTLENECK NODES</span>
            <span className="badge badge-amber">HIGH CONGESTION</span>
          </div>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart layout="vertical" data={data.top_bottlenecks || []} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="camera" width={150} tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'Fira Code' }} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#334155', color: '#fff', borderRadius: '8px', fontFamily: 'Fira Code' }} />
                <Bar dataKey="volume" fill="#00e5ff" barSize={12} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Metric Card 3: Vehicle Distribution (Donut Chart with Legend) */}
        <div className="analytics-card glass-card">
          <div className="card-top">
            <span className="card-label"><Car size={16} color="#00f0ff" /> VEHICLE DISTRIBUTION</span>
            <span className="badge badge-cyan">CLASSIFIED</span>
          </div>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data.fleet_distribution || []}
                  dataKey="count"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={90}
                  paddingAngle={4}
                >
                  {(data.fleet_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={NEON_COLORS[index % NEON_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#334155', color: '#fff', borderRadius: '8px', fontFamily: 'Fira Code' }} />
                <Legend verticalAlign="middle" align="right" layout="vertical" iconType="circle" wrapperStyle={{ color: '#cbd5e1', fontSize: '13px', fontFamily: 'Inter' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Telemetry Flow Trend (AreaChart with Gradient) */}
        <div className="analytics-card glass-card span-col-3">
          <div className="card-top">
            <span className="card-label"><TrendingUp size={16} color="#00e5ff" /> TELEMETRY FLOW TREND</span>
            <span className="badge badge-blue">REAL-TIME FLOW RATE</span>
          </div>
          <div style={{ width: '100%', height: 250 }}>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={data.telemetry_trend || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#00e5ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#475569" fontSize={12} />
                <YAxis stroke="#475569" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#334155', color: '#fff', borderRadius: '8px', fontFamily: 'Fira Code' }} />
                <Area type="monotone" dataKey="count" stroke="#00e5ff" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
