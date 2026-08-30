import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { Circle, CircleMarker, LayerGroup, MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png', iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png' })

export function MapFitter({ geojsonData }) {
  const map = useMap()
  const targetPlate = geojsonData?.properties?.target_plate || geojsonData?.target_plate || null
  const fittedPlateRef = useRef(null)

  useEffect(() => {
    if (!geojsonData || !targetPlate) {
      fittedPlateRef.current = null
      return
    }

    if (fittedPlateRef.current !== targetPlate) {
      const bounds = L.geoJSON(geojsonData).getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 13 })
        fittedPlateRef.current = targetPlate
      }
    }
  }, [geojsonData, targetPlate, map])

  return null
}
const pointFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'Point') || []
const lineFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'LineString') || []
const heatColor = intensity => ({ HIGH:'#ff2a2a', MEDIUM:'#ff9f0a', LOW:'#36ff9b' }[String(intensity).toUpperCase()] || '#ffb000')
const flowColor = (trips, maxTrips) => { const ratio = Math.min(1, Number(trips || 0) / Math.max(1, maxTrips)); const red = 255; const green = Math.round(176 - ratio * 134); return `rgb(${red}, ${green}, 0)` }
const radarIcon = recovered => L.divIcon({ className: 'trajectory-radar-icon', html: `<span class="radar-dot ${recovered ? 'radar-dot--amber' : ''}"></span>`, iconSize: [18, 18], iconAnchor: [9, 9] })

const getProbabilityColor = (prob) => {
  const p = Number(prob || 0)
  if (p >= 0.5) return '#ff2a2a' // High-Alert Red (>= 50%)
  if (p >= 0.2) return '#ff9f0a' // Orange (20% - 49%)
  return '#ffd60a'              // Yellow (< 20%)
}

function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

function TrajectoryLayer({ route, blacklist = [] }) {
  const points = pointFeatures(route)
  const allLines = lineFeatures(route)
  const targetPlate = route?.properties?.target_plate || route?.target_plate || ''
  if (!route) return null

  // Categorize line features
  const mainLines = allLines.filter(f => !f.properties?.is_forecast && !f.properties?.is_interpolated)
  const blindSpotLines = allLines.filter(f => f.properties?.is_interpolated)
  const forecastLines = allLines.filter(f => f.properties?.is_forecast)

  // Guardrail 1: Blacklist check
  const isBlacklisted = Array.isArray(blacklist) && blacklist.length > 0
    ? blacklist.some(b => b.plate_text?.trim().toUpperCase() === targetPlate?.trim().toUpperCase())
    : (route?.properties?.is_blacklisted ?? true)

  // Guardrail 2: Data Decay check (2-hour window)
  const latestSighting = points.length > 0
    ? points.slice().sort((a, b) => new Date(b.properties?.timestamp || 0) - new Date(a.properties?.timestamp || 0))[0]
    : null
  const latestTimestamp = latestSighting?.properties?.timestamp || route?.properties?.timestamp || route?.timestamp
  const hoursElapsed = latestTimestamp
    ? (Date.now() - new Date(latestTimestamp).getTime()) / (1000 * 60 * 60)
    : 0

  const isFresh = hoursElapsed <= 2
  const showPredictions = isFresh

  const rawForecast = route?.forecast?.predictions || route?.properties?.forecast?.predictions || route?.probabilistic_nodes || route?.properties?.probabilistic_nodes || []
  const forecastNodes = Array.isArray(rawForecast) ? rawForecast : []
  
  const lastPoint = points.length > 0 ? points[points.length - 1].geometry.coordinates : [80.2707, 13.0827]
  const lastLat = lastPoint[1]
  const lastLng = lastPoint[0]

  // Calculate dynamic radius to reach furthest forecast node + 10% padding
  let zoneRadiusMeters = 0
  if (forecastNodes.length > 0) {
    let maxDist = 0
    forecastNodes.forEach(node => {
      const nLat = Number(node.latitude ?? node.lat)
      const nLng = Number(node.longitude ?? node.lon ?? node.lng)
      if (!isNaN(nLat) && !isNaN(nLng)) {
        const d = haversineDistanceMeters(lastLat, lastLng, nLat, nLng)
        if (d > maxDist) maxDist = d
      }
    })
    zoneRadiusMeters = Math.max(600, maxDist * 1.10)
  }

  return (
    <LayerGroup key={targetPlate || 'trajectory'}>
      {/* Dynamic AI Probability Zone */}
      {showPredictions && forecastNodes.length > 0 && zoneRadiusMeters > 0 && (
        <Circle
          center={[lastLat, lastLng]}
          radius={zoneRadiusMeters}
          interactive={false}
          pathOptions={{
            color: '#a855f7',
            weight: 1.5,
            fillColor: '#a855f7',
            fillOpacity: 0.10,
            dashArray: '6, 6',
            className: 'radar-pulse predictive-cone-polygon'
          }}
        />
      )}

      {/* 1. Confirmed Sightings Route (Solid / Amber) */}
      {mainLines.map((feature, index) => (
        <Polyline
          key={`main-route-${index}`}
          positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
          pathOptions={{ color: '#ffaa00', weight: 4.5, opacity: 0.95, lineCap: 'round', dashArray: '10, 8' }}
        />
      ))}

      {/* 2. Blind-Spot Interpolated Route Segments (Cyan / Purple with road geometry) */}
      {blindSpotLines.map((feature, index) => {
        const p = feature.properties || {}
        return (
          <Polyline
            key={`blind-spot-${index}`}
            positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
            pathOptions={{
              color: '#00f0ff',
              weight: 5,
              opacity: 0.9,
              lineCap: 'round',
              dashArray: '6, 6',
              className: 'blind-spot-interpolated-path'
            }}
          >
            <Tooltip direction="top" opacity={0.95}>
              <div className="font-mono text-xs p-1" style={{ maxWidth: '240px' }}>
                <div className="font-bold text-[#00f0ff] flex items-center gap-1">
                  <span>🕶️ BLIND-SPOT RECONSTRUCTION</span>
                </div>
                <div className="text-gray-200 mt-1">
                  <b>{p.source_camera}</b> &rarr; <b>{p.target_camera}</b>
                </div>
                <div className="text-amber-300 mt-0.5">
                  Road Dist: <b>{p.road_distance_km} km</b> · Est: <b>{p.estimated_duration_minutes} min</b>
                </div>
                <div className="text-emerald-400 text-[11px] mt-0.5">
                  AI Confidence: <b>{p.confidence_percent || (p.confidence ? (p.confidence * 100).toFixed(0) : 90)}%</b>
                </div>
                <div className="text-slate-400 text-[10px] mt-0.5">
                  {p.explanation || 'Path interpolated via GIS road network constraints'}
                </div>
              </div>
            </Tooltip>
          </Polyline>
        )
      })}

      {/* 3. AI Predictive Forecast Trajectory Vectors (Glowing Magenta Future Path) */}
      {showPredictions && forecastLines.map((feature, index) => {
        const p = feature.properties || {}
        const isTop = p.forecast_rank === 1
        return (
          <Polyline
            key={`forecast-vector-${index}`}
            positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
            pathOptions={{
              color: isTop ? '#ec4899' : '#d946ef',
              weight: isTop ? 4 : 3,
              opacity: isTop ? 0.95 : 0.75,
              lineCap: 'round',
              dashArray: '8, 8',
              className: isTop ? 'forecast-pulse-line' : ''
            }}
          >
            <Tooltip direction="top" opacity={0.95}>
              <div className="font-mono text-xs p-1">
                <div className="font-bold text-[#ec4899]">
                  🔮 AI FORECAST VECTOR #{p.forecast_rank}
                </div>
                <div className="text-white font-semibold mt-0.5">
                  {p.target_name || p.target_camera}
                </div>
                <div className="text-cyan-400 mt-0.5">
                  Likelihood: <b>{p.probability_percent || Math.round((p.probability || 0) * 100)}%</b>
                </div>
                <div className="text-amber-400 text-[11px] mt-0.5">
                  ETA: <b>{p.eta_minutes} min</b> · Dist: <b>{p.distance_km} km</b>
                </div>
              </div>
            </Tooltip>
          </Polyline>
        )
      })}

      {/* 4. AI Forecasted Next Intersection Pins */}
      {showPredictions && forecastNodes.map((node, index) => {
        const lat = Number(node.latitude ?? node.lat ?? lastLat)
        const lng = Number(node.longitude ?? node.lon ?? node.lng ?? lastLng)
        if (isNaN(lat) || isNaN(lng)) return null
        const prob = Number(node.probability ?? 0)
        const color = getProbabilityColor(prob)
        const percent = node.probability_percent || Math.round(prob * 100)
        const name = node.camera_name || node.name || node.camera_id || `Intersection ${index + 1}`
        const eta = node.eta_minutes || (node.distance_km ? (node.distance_km / 0.7).toFixed(1) : 3.0)

        return (
          <CircleMarker
            key={node.camera_id ? `forecast-node-${node.camera_id}` : `forecast-node-${index}`}
            center={[lat, lng]}
            radius={prob >= 0.5 ? 11 : 9}
            pathOptions={{
              color: '#d946ef',
              weight: 2.5,
              fillColor: color,
              fillOpacity: 0.9,
              className: prob >= 0.5 ? 'radar-pulse' : ''
            }}
          >
            <Tooltip direction="top" opacity={0.95}>
              <div className="font-mono text-xs text-center p-1">
                <div className="text-[#ec4899] font-bold text-[10px]">PREDICTED NEXT INTERSECTION</div>
                <b className="text-white">{name}</b>
                <div className="mt-1 flex items-center justify-center gap-2">
                  <span style={{ color: color, fontWeight: 700 }}>{percent}% Probability</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-cyan-300 font-bold">ETA: {eta} min</span>
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}

      {/* 5. Confirmed Camera Sighting Pins */}
      {points.map((point, index) => {
        const [lng, lat] = point.geometry.coordinates
        const isLast = index === points.length - 1
        if (isLast) {
          return (
            <CircleMarker
              key={point.properties?.event_id || `${lng}-${lat}-last`}
              center={[lat, lng]}
              radius={9}
              color="#ff0044"
              fillColor="#ff0044"
              fillOpacity={0.95}
              className="pulse-node"
            >
              <Tooltip direction="top">
                <div className="font-mono text-xs">
                  <b className="text-red-400">LAST SEEN: {point.properties?.camera_name}</b>
                  <br />
                  <span className="text-white">{point.properties?.detected_plate}</span>
                  <br />
                  <small className="text-slate-400">{point.properties?.timestamp}</small>
                </div>
              </Tooltip>
            </CircleMarker>
          )
        }
        return (
          <CircleMarker
            key={point.properties?.event_id || `${lng}-${lat}`}
            center={[lat, lng]}
            radius={7}
            pathOptions={{ color: '#ffd700', fillColor: '#ffd700', fillOpacity: 0.85, weight: 2 }}
          >
            <Tooltip direction="top">
              <div className="font-mono text-xs">
                <b>{point.properties?.camera_name}</b>
                <br />
                <span className="text-amber-400">{point.properties?.detected_plate}</span>
                {point.properties?.segment_speed_kmh > 0 && (
                  <div className="text-cyan-300 text-[10px] mt-0.5">
                    Speed: {point.properties.segment_speed_kmh} km/h
                  </div>
                )}
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </LayerGroup>
  )
}

function HeatmapLayer({ heatNodes, odCorridors, cameras }) {
  const cameraByName = useMemo(() => new Map(cameras.map(camera => [camera.name?.trim().toLowerCase(), camera])), [cameras])
  const maxTrips = Math.max(1, ...odCorridors.map(corridor => Number(corridor.total_trips || 0)))
  return (
    <LayerGroup>
      {heatNodes.map(node => {
        const vpm = Number(node.vehicles_per_minute || 0)
        const color = heatColor(node.congestion_intensity)
        return (
          <CircleMarker
            key={node.camera_id}
            center={[node.lat, node.lon]}
            radius={Math.min(68, 17 + vpm * 1.65)}
            className="heatmap-blob"
            stroke={false}
            fillColor={color}
            fillOpacity={0.3}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
              <div className="font-mono text-xs">
                <div className="font-bold text-cyan-400">{node.name || node.camera_name || node.camera_id}</div>
                <div className="text-gray-300">
                  {vpm} vehicles/min · {node.congestion_intensity}
                </div>
                <div className="text-gray-300">
                  Avg Transit Speed: <span className="text-amber-400 font-semibold">
                    {node.avg_corridor_speed_kmh ? `${node.avg_corridor_speed_kmh} km/h` : 'N/A'}
                  </span>
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </LayerGroup>
  )
}

export default function SentinelMap({ cameras, route, heatNodes, odCorridors, activeTab, blacklist = [] }) {
  return (
    <MapContainer className="sentinel-map" center={[13.0827, 80.2707]} zoom={11} zoomControl={false}>
      <TileLayer
        attribution='&copy; <a href="https://www.maptiler.com/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url={`https://api.maptiler.com/maps/dataviz-dark/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_KEY || 'BppDaPHRJXTmc6VI4uvP'}`}
      />
      {activeTab === 'heat' ? (
        <HeatmapLayer heatNodes={heatNodes} odCorridors={odCorridors} cameras={cameras}/>
      ) : (
        <LayerGroup>
          {cameras.map(camera => (
            <CircleMarker
              key={camera.camera_id}
              center={[camera.latitude, camera.longitude]}
              radius={7}
              pathOptions={{ color: '#00f0ff', fillColor: '#00f0ff', fillOpacity: 0.7, weight: 2 }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                <div className="font-mono text-xs">
                  <div className="font-bold text-cyan-400">{camera.name || camera.camera_name || camera.camera_id}</div>
                  <div className="text-gray-300">
                    Avg Transit Speed: <span className="text-amber-400 font-semibold">
                      {camera.avg_corridor_speed_kmh ? `${camera.avg_corridor_speed_kmh} km/h` : 'N/A'}
                    </span>
                  </div>
                </div>
              </Tooltip>
            </CircleMarker>
          ))}
        </LayerGroup>
      )}
      <TrajectoryLayer route={route} blacklist={blacklist}/>
      <MapFitter geojsonData={route}/>
    </MapContainer>
  )
}
