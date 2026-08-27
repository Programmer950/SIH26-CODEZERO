import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, CircleMarker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default Leaflet marker icon issue with bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom numbered marker icon — route waypoints
function createNumberedIcon(number, isActive = false) {
  return L.divIcon({
    className: "custom-marker",
    html: `<div style="
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: ${isActive ? "#2563eb" : "#1e293b"};
      border: 2.5px solid ${isActive ? "#93c5fd" : "#475569"};
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      font-family: 'Inter', system-ui, sans-serif;
      box-shadow: ${isActive
        ? "0 0 0 4px rgba(59,130,246,0.25), 0 4px 12px rgba(0,0,0,0.5)"
        : "0 2px 8px rgba(0,0,0,0.5)"
      };
      transition: all 0.3s ease;
    ">${number}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

// Camera marker icon — labeled with ID
function createCameraIcon(camera) {
  const isOnline = camera.status === "online";
  const color = isOnline ? "#10b981" : "#ef4444";
  return L.divIcon({
    className: "custom-marker",
    html: `<div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
    ">
      <div style="
        width: 24px;
        height: 24px;
        border-radius: 6px;
        background: #111827;
        border: 1.5px solid ${color};
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 10px ${color}40, 0 2px 8px rgba(0,0,0,0.4);
      ">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.934a.5.5 0 0 0-.777-.416L16 11"/>
          <rect x="2" y="6" width="14" height="12" rx="2"/>
        </svg>
      </div>
      <div style="
        font-size: 9px;
        font-weight: 700;
        font-family: 'Inter', system-ui, sans-serif;
        color: ${isOnline ? "#94a3b8" : "#ef444480"};
        letter-spacing: 0.5px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        background: rgba(15,18,25,0.85);
        padding: 1px 4px;
        border-radius: 3px;
      ">${camera.id}</div>
    </div>`,
    iconSize: [40, 38],
    iconAnchor: [20, 19],
  });
}

// Density circle color mapping
const densityColors = {
  "very-high": { stroke: "#ef4444", fill: "#ef4444" },
  high: { stroke: "#f59e0b", fill: "#f59e0b" },
  medium: { stroke: "#3b82f6", fill: "#3b82f6" },
  low: { stroke: "#10b981", fill: "#10b981" },
};

/**
 * MapView — reusable Leaflet map component
 *
 * Props:
 * - center: [lat, lng]
 * - zoom: number
 * - cameras: array of camera objects (shown as labeled icons)
 * - route: array of { latitude, longitude, cameraId, ... } (shown as numbered markers + polyline)
 * - activeRouteStep: number (highlights the active marker)
 * - trafficZones: array of { latitude, longitude, density, radius, name, vehicleCount }
 * - height: CSS height string
 * - vehicleInfo: { number, ... } for popups
 */
export default function MapView({
  center = [13.05, 80.23],
  zoom = 12,
  cameras = [],
  route = [],
  activeRouteStep = -1,
  trafficZones = [],
  height = "100%",
  vehicleInfo = null,
}) {
  const routePositions = route.map((d) => [d.latitude, d.longitude]);

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ height, width: "100%" }}
      className="rounded-lg"
      zoomControl={false}
    >
      {/* Dark map tiles — CartoDB Dark Matter */}
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />

      {/* Camera markers */}
      {cameras.map((cam) => (
        <Marker
          key={cam.id}
          position={[cam.latitude, cam.longitude]}
          icon={createCameraIcon(cam)}
        >
          <Popup>
            <div className="map-popup-content">
              <div className="map-popup-header">{cam.id}</div>
              <div className="map-popup-subtext">{cam.name}</div>
              <div className="map-popup-divider"></div>
              <div className="map-popup-row">
                <span className="map-popup-label">Status</span>
                <span className={cam.status === "online" ? "map-popup-val-green" : "map-popup-val-red"}>
                  {cam.status === "online" ? "● Online" : "● Offline"}
                </span>
              </div>
              {cam.status === "online" && (
                <div className="map-popup-row">
                  <span className="map-popup-label">Vehicles</span>
                  <span className="map-popup-val">{cam.vehiclesDetected}</span>
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Route polyline — gradient-like dashed line */}
      {routePositions.length > 1 && (
        <Polyline
          positions={routePositions}
          color="#3b82f6"
          weight={3}
          opacity={0.6}
          dashArray="10 8"
        />
      )}

      {/* Route numbered markers */}
      {route.map((detection, index) => (
        <Marker
          key={`route-${index}`}
          position={[detection.latitude, detection.longitude]}
          icon={createNumberedIcon(index + 1, activeRouteStep === index)}
        >
          <Popup>
            <div className="map-popup-content">
              <div className="map-popup-header">{detection.cameraId}</div>
              {vehicleInfo && (
                <div className="map-popup-subtext" style={{ fontFamily: "monospace", letterSpacing: "0.05em" }}>
                  {vehicleInfo.number}
                </div>
              )}
              <div className="map-popup-divider"></div>
              <div className="map-popup-row">
                <span className="map-popup-label">Time</span>
                <span className="map-popup-val">{detection.timestamp}</span>
              </div>
              <div className="map-popup-row">
                <span className="map-popup-label">Confidence</span>
                <span className="map-popup-val-green">{detection.confidence}%</span>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Traffic density circles — dual-ring style */}
      {trafficZones.map((zone) => {
        const colors = densityColors[zone.density] || densityColors.medium;
        return (
          <React.Fragment key={zone.id}>
            {/* Outer glow ring */}
            <Circle
              center={[zone.latitude, zone.longitude]}
              radius={zone.radius}
              pathOptions={{
                color: colors.stroke,
                fillColor: colors.fill,
                fillOpacity: 0.12,
                weight: 1,
                opacity: 0.4,
              }}
            />
            {/* Inner core */}
            <Circle
              center={[zone.latitude, zone.longitude]}
              radius={zone.radius * 0.5}
              pathOptions={{
                color: colors.stroke,
                fillColor: colors.fill,
                fillOpacity: 0.25,
                weight: 1.5,
                opacity: 0.7,
              }}
            >
              <Popup>
                <div className="map-popup-content">
                  <div className="map-popup-header">{zone.name}</div>
                  <div className="map-popup-divider"></div>
                  <div className="map-popup-row">
                    <span className="map-popup-label">Density</span>
                    <span className="map-popup-val" style={{ textTransform: "capitalize" }}>
                      {zone.density.replace("-", " ")}
                    </span>
                  </div>
                  <div className="map-popup-row">
                    <span className="map-popup-label">Vehicles</span>
                    <span className="map-popup-val">{zone.vehicleCount.toLocaleString()}</span>
                  </div>
                </div>
              </Popup>
            </Circle>
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}
