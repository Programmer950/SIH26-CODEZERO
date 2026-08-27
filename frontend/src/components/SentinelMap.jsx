import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png', iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png' })

export function MapFitter({ geojsonData }) { const map = useMap(); useEffect(() => { if (!geojsonData) return; const bounds = L.geoJSON(geojsonData).getBounds(); if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50] }) }, [geojsonData, map]); return null }
const pointFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'Point') || []
const lineFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'LineString') || []
const heatColor = intensity => ({ HIGH:'#ff2a2a', MEDIUM:'#ff9f0a', LOW:'#36ff9b' }[String(intensity).toUpperCase()] || '#ffb000')
const flowColor = (trips, maxTrips) => { const ratio = Math.min(1, Number(trips || 0) / Math.max(1, maxTrips)); const red = 255; const green = Math.round(176 - ratio * 134); return `rgb(${red}, ${green}, 0)` }
const radarIcon = recovered => L.divIcon({ className: 'trajectory-radar-icon', html: `<span class="radar-dot ${recovered ? 'radar-dot--amber' : ''}"></span>`, iconSize: [18, 18], iconAnchor: [9, 9] })

function TrajectoryLayer({ route }) {
  const points = pointFeatures(route); const lines = lineFeatures(route); const targetPlate = route?.properties?.target_plate
  if (!route) return null
  return <LayerGroup key={targetPlate || 'trajectory'}>{lines.map((feature, index) => <Polyline key={`route-${index}`} positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])} pathOptions={{ color: '#00f0ff', weight: 4, opacity: .95, lineCap: 'round' }}/>) }{points.map(point => { const [lng, lat] = point.geometry.coordinates; const recovered = point.properties?.detected_plate !== targetPlate; return <Marker key={point.properties?.event_id || `${lng}-${lat}`} position={[lat, lng]} icon={radarIcon(recovered)}><Tooltip direction="top"><b>{point.properties?.camera_name}</b><br/>{point.properties?.detected_plate}</Tooltip></Marker> })}</LayerGroup>
}

function HeatmapLayer({ heatNodes, odCorridors, cameras }) {
  const cameraByName = useMemo(() => new Map(cameras.map(camera => [camera.name?.trim().toLowerCase(), camera])), [cameras])
  const maxTrips = Math.max(1, ...odCorridors.map(corridor => Number(corridor.total_trips || 0)))
  return <LayerGroup>{heatNodes.map(node => { const vpm = Number(node.vehicles_per_minute || 0); const color = heatColor(node.congestion_intensity); return <CircleMarker key={node.camera_id} center={[node.lat, node.lon]} radius={Math.min(68, 17 + vpm * 1.65)} className="heatmap-blob" stroke={false} fillColor={color} fillOpacity={.5}><Tooltip direction="top"><b>{node.name}</b><br/>{vpm} vehicles/min · {node.congestion_intensity}</Tooltip></CircleMarker> })}</LayerGroup>
}

export default function SentinelMap({ cameras, route, heatNodes, odCorridors, activeTab }) { return <MapContainer className="sentinel-map" center={[13.0827,80.2707]} zoom={11} zoomControl={false}><TileLayer attribution={'&copy; <a href="https://www.esri.com/">Esri</a>'} url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"/>
  {activeTab === 'heat' ? <HeatmapLayer heatNodes={heatNodes} odCorridors={odCorridors} cameras={cameras}/> : <LayerGroup>{cameras.map(camera => <CircleMarker key={camera.camera_id} center={[camera.latitude, camera.longitude]} radius={7} pathOptions={{ color:'#00f0ff', fillColor:'#00f0ff', fillOpacity:.7, weight:2 }}><Tooltip><b>{camera.name}</b><br/>{camera.camera_id} · {camera.speed_limit_kmh} km/h</Tooltip></CircleMarker>)}</LayerGroup>}
  <TrajectoryLayer route={route}/><MapFitter geojsonData={route}/>
 </MapContainer> }
