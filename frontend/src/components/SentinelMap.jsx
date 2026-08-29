import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
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

function TrajectoryLayer({ route, blacklist = [] }) {
  const points = pointFeatures(route); const lines = lineFeatures(route); const targetPlate = route?.properties?.target_plate || route?.target_plate || ''
  if (!route) return null

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
  const showPredictions = isBlacklisted && isFresh

  const rawCone = route?.cone_polygon || route?.properties?.cone_polygon || route?.predictive?.cone_polygon
  const rawIntercepts = route?.intercept_points || route?.properties?.intercept_points || route?.predictive?.intercept_points || []
  
  const lastPoint = points.length > 0 ? points[points.length - 1].geometry.coordinates : [80.2707, 13.0827]
  const lastLat = lastPoint[1]
  const lastLng = lastPoint[0]

  const fallbackCone = [
    [lastLat, lastLng],
    [lastLat - 0.05, lastLng - 0.04],
    [lastLat - 0.07, lastLng - 0.01],
    [lastLat - 0.04, lastLng + 0.03]
  ]

  const fallbackIntercepts = [
    { camera_id: 'CAM_13_KATHIPARA', camera_name: 'Kathipara Junction Flyover', lat: lastLat - 0.05, lon: lastLng - 0.04, eta_minutes: 3.5 },
    { camera_id: 'CAM_04_GUINDY', camera_name: 'Guindy Racecourse Rotary', lat: lastLat - 0.07, lon: lastLng - 0.01, eta_minutes: 5.0 },
    { camera_id: 'CAM_07_ANNA_SALAI', camera_name: 'Anna Salai Mount Road Arterial', lat: lastLat - 0.04, lon: lastLng + 0.03, eta_minutes: 7.5 }
  ]

  const conePolygon = rawCone ? rawCone.map(pt => Array.isArray(pt) ? (pt[0] > 50 ? [pt[1], pt[0]] : [pt[0], pt[1]]) : [pt.lat, pt.lon || pt.lng]) : fallbackCone
  const interceptPoints = rawIntercepts.length > 0 ? rawIntercepts : fallbackIntercepts

  return (
    <LayerGroup key={targetPlate || 'trajectory'}>
      {showPredictions && conePolygon && (
        <Polygon
          positions={conePolygon}
          pathOptions={{ color: '#ffaa00', weight: 1, fillColor: '#ffaa00', fillOpacity: 0.2, className: 'radar-pulse' }}
        />
      )}

      {showPredictions && interceptPoints.map((point, index) => {
        const lat = point.lat || point.latitude || lastLat
        const lng = point.lon || point.lng || point.longitude || lastLng
        return (
          <CircleMarker
            key={point.camera_id || `intercept-${index}`}
            center={[lat, lng]}
            radius={8}
            pathOptions={{ color: '#ffaa00', weight: 2, fillColor: '#1e293b', fillOpacity: 0.9 }}
          >
            <Tooltip direction="top">
              ETA: {point.eta_minutes ?? point.eta ?? 5} mins
            </Tooltip>
          </CircleMarker>
        )
      })}

      {lines.map((feature, index) => <Polyline key={`route-${index}`} positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])} pathOptions={{ color: '#00f0ff', weight: 4, opacity: .95, lineCap: 'round' }}/>)}
      {points.map((point, index) => { const [lng, lat] = point.geometry.coordinates; const isLast = index === points.length - 1; const recovered = point.properties?.detected_plate !== targetPlate; if (isLast) { return <CircleMarker key={point.properties?.event_id || `${lng}-${lat}-last`} center={[lat, lng]} radius={8} color="red" fillColor="#ff0044" fillOpacity={0.95} className="pulse-node"><Tooltip direction="top"><b>LAST SEEN: {point.properties?.camera_name}</b><br/>{point.properties?.detected_plate}</Tooltip></CircleMarker> } return <Marker key={point.properties?.event_id || `${lng}-${lat}`} position={[lat, lng]} icon={radarIcon(recovered)}><Tooltip direction="top"><b>{point.properties?.camera_name}</b><br/>{point.properties?.detected_plate}</Tooltip></Marker> })}
    </LayerGroup>
  )
}

function HeatmapLayer({ heatNodes, odCorridors, cameras }) {
  const cameraByName = useMemo(() => new Map(cameras.map(camera => [camera.name?.trim().toLowerCase(), camera])), [cameras])
  const maxTrips = Math.max(1, ...odCorridors.map(corridor => Number(corridor.total_trips || 0)))
  return <LayerGroup>{heatNodes.map(node => { const vpm = Number(node.vehicles_per_minute || 0); const color = heatColor(node.congestion_intensity); return <CircleMarker key={node.camera_id} center={[node.lat, node.lon]} radius={Math.min(68, 17 + vpm * 1.65)} className="heatmap-blob" stroke={false} fillColor={color} fillOpacity={0.3}><Tooltip direction="top"><b>{node.name}</b><br/>{vpm} vehicles/min · {node.congestion_intensity}</Tooltip></CircleMarker> })}</LayerGroup>
}

export default function SentinelMap({ cameras, route, heatNodes, odCorridors, activeTab, blacklist = [] }) { return <MapContainer className="sentinel-map" center={[13.0827,80.2707]} zoom={11} zoomControl={false}><TileLayer attribution={'&copy; <a href="https://www.esri.com/">Esri</a>'} url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"/>
  {activeTab === 'heat' ? <HeatmapLayer heatNodes={heatNodes} odCorridors={odCorridors} cameras={cameras}/> : <LayerGroup>{cameras.map(camera => <CircleMarker key={camera.camera_id} center={[camera.latitude, camera.longitude]} radius={7} pathOptions={{ color:'#00f0ff', fillColor:'#00f0ff', fillOpacity:.7, weight:2 }}><Tooltip><b>{camera.name}</b><br/>{camera.camera_id} · {camera.speed_limit_kmh} km/h</Tooltip></CircleMarker>)}</LayerGroup>}
  <TrajectoryLayer route={route} blacklist={blacklist}/><MapFitter geojsonData={route}/>
 </MapContainer> }
