import { useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, GeoJSON } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
const position = (camera) => [Number(camera.latitude ?? camera.lat ?? camera.location?.latitude), Number(camera.longitude ?? camera.lng ?? camera.location?.longitude)]
export default function CommandMap({ cameras, heatmap, trajectory, onCameraSelect }) {
  const points = useMemo(() => (trajectory?.features || []).flatMap(f => { const c = f.geometry?.coordinates; return c?.length >= 2 ? [[c[1], c[0]]] : [] }), [trajectory])
  return <MapContainer center={[20.5937, 78.9629]} zoom={5} className="command-map" zoomControl={false}>
    <TileLayer
      attribution='&copy; <a href="https://www.maptiler.com/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url={`https://api.maptiler.com/maps/dataviz-dark/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_KEY || 'BppDaPHRJXTmc6VI4uvP'}`}
    />
    {(cameras || []).map((camera, index) => { const pos = position(camera); if (pos.some(Number.isNaN)) return null; return <CircleMarker key={camera.id || camera.camera_id || index} center={pos} radius={8} pathOptions={{ color: '#00f0ff', fillColor: '#00f0ff', fillOpacity: .6, weight: 2 }} eventHandlers={{ click: () => onCameraSelect(camera) }}><Popup><b>{camera.name || camera.camera_name || 'Camera node'}</b><br/>{camera.id || camera.camera_id}</Popup></CircleMarker> })}
    {(heatmap?.features || []).map((f, i) => { const c = f.geometry?.coordinates; if (!c) return null; return <CircleMarker key={`heat-${i}`} center={[c[1], c[0]]} radius={Math.max(7, Number(f.properties?.weight || f.properties?.count || 1) * 2)} pathOptions={{ color: '#ffb000', fillColor: '#ff6b00', fillOpacity: .23, weight: 1 }} /> })}
    {points.length > 1 && <Polyline positions={points} pathOptions={{ color: '#ffaa00', weight: 4, dashArray: '10, 10' }} />}
    {trajectory?.type === 'FeatureCollection' && <GeoJSON data={trajectory} style={{ color: '#ffaa00', weight: 3 }}/>} 
  </MapContainer>
}
