import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
})

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

const pointFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'Point' && !feature.properties?.is_forecast_intersection) || []
const forecastPointFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'Point' && feature.properties?.is_forecast_intersection) || []
const lineFeatures = route => route?.features?.filter(feature => feature.geometry?.type === 'LineString') || []

const heatColor = intensity => ({ HIGH: '#ff2a2a', MEDIUM: '#ff9f0a', LOW: '#36ff9b' }[String(intensity).toUpperCase()] || '#ffb000')
const radarIcon = recovered => L.divIcon({ className: 'trajectory-radar-icon', html: `<span class="radar-dot ${recovered ? 'radar-dot--amber' : ''}"></span>`, iconSize: [18, 18], iconAnchor: [9, 9] })
const forecastIcon = () => L.divIcon({ className: 'forecast-radar-icon', html: `<span class="radar-dot radar-dot--purple pulse-ring"></span>`, iconSize: [22, 22], iconAnchor: [11, 11] })

function TrajectoryLayer({ route, blacklist = [] }) {
  const points = pointFeatures(route)
  const forecastPoints = forecastPointFeatures(route)
  const lines = lineFeatures(route)
  const targetPlate = route?.properties?.target_plate || route?.target_plate || ''
  
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
  const rawIntercepts = route?.intercept_points || route?.properties?.intercept_points || route?.properties?.predictions?.next_intersections || []
  
  const lastPoint = points.length > 0 ? points[points.length - 1].geometry.coordinates : [80.2707, 13.0827]
  const lastLat = lastPoint[1]
  const lastLng = lastPoint[0]

  const fallbackCone = [
    [lastLat, lastLng],
    [lastLat - 0.05, lastLng - 0.04],
    [lastLat - 0.07, lastLng - 0.01],
    [lastLat - 0.04, lastLng + 0.03]
  ]

  const conePolygon = rawCone ? rawCone.map(pt => Array.isArray(pt) ? (pt[0] > 50 ? [pt[1], pt[0]] : [pt[0], pt[1]]) : [pt.lat, pt.lon || pt.lng]) : fallbackCone

  // Separate line categories
  const blindSpotLines = lines.filter(f => f.properties?.is_blind_spot)
  const forecastLines = lines.filter(f => f.properties?.is_forecast || f.properties?.route_type === 'PREDICTED_FUTURE_PATH')
  const historicalLines = lines.filter(f => !f.properties?.is_blind_spot && !f.properties?.is_forecast)

  return (
    <LayerGroup key={targetPlate || 'trajectory'}>
      {/* 1. Tactical Probability Cone */}
      {showPredictions && conePolygon && (
        <Polygon
          positions={conePolygon}
          pathOptions={{ color: '#ffaa00', weight: 1, fillColor: '#ffaa00', fillOpacity: 0.15, className: 'radar-pulse' }}
        />
      )}

      {/* 2. Main Historical Reconstructed Route (Cyan Solid Glow) */}
      {historicalLines.map((feature, index) => (
        <Polyline
          key={`hist-route-${index}`}
          positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
          pathOptions={{ color: '#00f0ff', weight: 4, opacity: 0.95, lineCap: 'round' }}
        />
      ))}

      {/* 3. GIS Blind-Spot Interpolated Paths (Amber Dashed Road Geometry) */}
      {blindSpotLines.map((feature, index) => (
        <Polyline
          key={`blind-spot-${index}`}
          positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
          pathOptions={{ color: '#ffaa00', weight: 4, opacity: 0.95, dashArray: '6, 8', lineCap: 'round' }}
        >
          <Tooltip direction="top" sticky>
            <b style={{ color: '#ffaa00' }}>[!] BLIND ZONE RECOVERED:</b> {feature.properties?.segment_name || 'GIS Shortest Path'}<br />
            Gap: <b>{feature.properties?.gap_distance_km} km</b> · Confidence: <b>{Math.round((feature.properties?.confidence || 0.85) * 100)}%</b>
          </Tooltip>
        </Polyline>
      ))}

      {/* 4. GNN / RNN Predicted Future Path (Neon Purple / Magenta Dashed Forecast) */}
      {showPredictions && forecastLines.map((feature, index) => (
        <Polyline
          key={`forecast-route-${index}`}
          positions={feature.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
          pathOptions={{ color: '#c026d3', weight: 4, opacity: 0.95, dashArray: '8, 8', lineCap: 'round' }}
        >
          <Tooltip direction="top" sticky>
            <b style={{ color: '#c026d3' }}>🔮 GNN/RNN FORECASTED ESCAPE VECTOR</b><br />
            Heading: <b>{feature.properties?.heading_deg || 0}°</b> · Model: <b>{feature.properties?.model || 'GNN_RNN_HYBRID'}</b>
          </Tooltip>
        </Polyline>
      ))}

      {/* 5. GNN / RNN Forecast Next Intersection Destination Markers */}
      {showPredictions && forecastPoints.map((point, index) => {
        const [lng, lat] = point.geometry.coordinates
        const props = point.properties || {}
        return (
          <CircleMarker
            key={`forecast-pin-${props.camera_id || index}`}
            center={[lat, lng]}
            radius={9}
            pathOptions={{ color: '#c026d3', weight: 2, fillColor: '#1e1b4b', fillOpacity: 0.95 }}
          >
            <Tooltip direction="top" permanent={index === 0}>
              <b style={{ color: '#e879f9' }}>NEXT INTERSECTION ({props.confidence_pct || 50}%)</b><br />
              <b>{props.camera_name || props.camera_id}</b><br />
              Distance: <b>{props.distance_km} km</b> · ETA: <b style={{ color: '#38bdf8' }}>{props.eta_minutes} mins</b>
            </Tooltip>
          </CircleMarker>
        )
      })}

      {/* 6. Tactical Intercept Points if available */}
      {showPredictions && rawIntercepts.slice(0, 3).map((point, index) => {
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
              <b style={{ color: '#ffaa00' }}>INTERCEPT CHOKEPOINT #{index + 1}</b><br />
              {point.camera_name || point.name}<br />
              ETA: <b>{point.eta_minutes ?? point.eta ?? 5} mins</b>
            </Tooltip>
          </CircleMarker>
        )
      })}

      {/* 7. Historical Camera Sighting Pins */}
      {points.map((point, index) => {
        const [lng, lat] = point.geometry.coordinates
        const isLast = index === points.length - 1
        const recovered = point.properties?.detected_plate !== targetPlate
        if (isLast) {
          return (
            <CircleMarker key={point.properties?.event_id || `${lng}-${lat}-last`} center={[lat, lng]} radius={9} color="red" fillColor="#ff0044" fillOpacity={0.95} className="pulse-node">
              <Tooltip direction="top">
                <b>LAST SIGHTING: {point.properties?.camera_name}</b><br />
                Plate: <b>{point.properties?.detected_plate}</b><br />
                {new Date(point.properties?.timestamp).toLocaleTimeString('en-IN')}
              </Tooltip>
            </CircleMarker>
          )
        }
        return (
          <Marker key={point.properties?.event_id || `${lng}-${lat}`} position={[lat, lng]} icon={radarIcon(recovered)}>
            <Tooltip direction="top">
              <b>#{point.properties?.sequence_order || index + 1}: {point.properties?.camera_name}</b><br />
              Plate: <b>{point.properties?.detected_plate}</b> ({Math.round((point.properties?.ocr_confidence || 0.9) * 100)}% OCR)<br />
              {new Date(point.properties?.timestamp).toLocaleTimeString('en-IN')}
            </Tooltip>
          </Marker>
        )
      })}
    </LayerGroup>
  )
}

function HeatmapLayer({ heatNodes, odCorridors, cameras }) {
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
            <Tooltip direction="top">
              <b>{node.name}</b><br />
              {vpm} vehicles/min · {node.congestion_intensity}
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
      <TileLayer attribution={'&copy; <a href="https://www.esri.com/">Esri</a>'} url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}" />
      {activeTab === 'heat' ? (
        <HeatmapLayer heatNodes={heatNodes} odCorridors={odCorridors} cameras={cameras} />
      ) : (
        <LayerGroup>
          {cameras.map(camera => (
            <CircleMarker key={camera.camera_id} center={[camera.latitude, camera.longitude]} radius={6} pathOptions={{ color: '#00f0ff', fillColor: '#00f0ff', fillOpacity: 0.6, weight: 1.5 }}>
              <Tooltip>
                <b>{camera.name}</b><br />
                {camera.camera_id} · {camera.speed_limit_kmh} km/h
              </Tooltip>
            </CircleMarker>
          ))}
        </LayerGroup>
      )}
      <TrajectoryLayer route={route} blacklist={blacklist} />
      <MapFitter geojsonData={route} />
    </MapContainer>
  )
}
