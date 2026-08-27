import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { MapPin, Car, Camera, TrendingUp } from "lucide-react";
import Navbar from "../components/Navbar";
import StatCard from "../components/StatCard";
import MapView from "../components/MapView";
import { getTrafficData, getCameras } from "../services/api";

const densityLabels = [
  { label: "Very High", color: "#ef4444" },
  { label: "High", color: "#f59e0b" },
  { label: "Medium", color: "#3b82f6" },
  { label: "Low", color: "#10b981" },
];

// Custom dark tooltip for Recharts
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-[#1e2433] border border-white/[0.08] rounded-lg px-3 py-2 text-[12px]">
      <div className="text-slate-400 mb-1">{label}</div>
      <div className="text-white font-semibold">
        {payload[0].value.toLocaleString()} vehicles
      </div>
    </div>
  );
};

export default function Traffic() {
  const [trafficData, setTrafficData] = useState(null);
  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    getTrafficData().then(setTrafficData);
    getCameras().then(setCameras);
  }, []);

  if (!trafficData) return null;

  const { hourlyTraffic, cameraTraffic, trafficZones, trafficStats } = trafficData;

  return (
    <div className="flex-1 min-h-screen bg-[#0f1219]">
      <Navbar title="Traffic Heatmap" />

      <div className="p-6">
        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">
            Traffic Intelligence
          </h2>
          <p className="text-[13px] text-slate-400 mt-1">
            Visualize traffic density and movement patterns
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={MapPin}
            value={trafficStats.peakZone}
            label="Peak Traffic Zone"
            color="red"
          />
          <StatCard
            icon={Car}
            value={trafficStats.totalVehicles}
            label="Vehicles Detected"
            color="blue"
          />
          <StatCard
            icon={Camera}
            value={trafficStats.activeCameras}
            label="Active Cameras"
            color="green"
          />
          <StatCard
            icon={TrendingUp}
            value={trafficStats.highDensityCameras}
            label="High Density Cameras"
            color="amber"
          />
        </div>

        {/* Map + Legend */}
        <div className="grid grid-cols-12 gap-5 mb-6">
          <div className="col-span-9">
            <div className="bg-[#111827] border border-white/[0.06] rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.04]">
                <h3 className="text-[13px] font-semibold text-white">
                  Traffic Density Map
                </h3>
              </div>
              <div className="h-[420px]">
                <MapView
                  cameras={cameras}
                  trafficZones={trafficZones}
                  zoom={12}
                />
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="col-span-3">
            <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-4">
              <h3 className="text-[13px] font-semibold text-white mb-4">
                Density Legend
              </h3>
              <div className="space-y-3">
                {densityLabels.map(({ label, color }) => (
                  <div key={label} className="flex items-center gap-3">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ background: color, opacity: 0.7 }}
                    />
                    <span className="text-[12px] text-slate-400">{label}</span>
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-4 border-t border-white/[0.06]">
                <h4 className="text-[11px] font-semibold text-slate-500 tracking-wider mb-3">
                  TOP ZONES
                </h4>
                <div className="space-y-2">
                  {trafficZones
                    .sort((a, b) => b.vehicleCount - a.vehicleCount)
                    .slice(0, 4)
                    .map((zone) => (
                      <div
                        key={zone.id}
                        className="flex items-center justify-between"
                      >
                        <span className="text-[12px] text-slate-400">
                          {zone.name}
                        </span>
                        <span className="text-[11px] font-mono text-slate-500">
                          {zone.vehicleCount.toLocaleString()}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-5">
          {/* Hourly line chart */}
          <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-white mb-4">
              Vehicles Detected by Hour
            </h3>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hourlyTraffic}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="hour"
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={{ stroke: "#1e293b" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={{ stroke: "#1e293b" }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="vehicles"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#3b82f6" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Camera bar chart */}
          <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-white mb-4">
              Vehicle Count by Camera
            </h3>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cameraTraffic}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="camera"
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={{ stroke: "#1e293b" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={{ stroke: "#1e293b" }}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar
                    dataKey="vehicles"
                    fill="#3b82f6"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
