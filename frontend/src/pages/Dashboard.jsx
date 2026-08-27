import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, Car, Route, ShieldAlert, ArrowRight } from "lucide-react";
import Navbar from "../components/Navbar";
import StatCard from "../components/StatCard";
import CameraCard from "../components/CameraCard";
import MapView from "../components/MapView";
import { getCameras, getAlerts } from "../services/api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getCameras().then(setCameras);
    getAlerts().then(setAlerts);
  }, []);

  const recentAlerts = alerts.slice(0, 3);

  return (
    <div className="flex-1 min-h-screen bg-[#0f1219]">
      <Navbar title="Dashboard" />

      <div className="p-6">
        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">Live Monitoring</h2>
          <p className="text-[13px] text-slate-400 mt-1">
            Real-time vehicle intelligence across connected cameras
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard icon={Camera} value={24} label="Cameras Online" color="green" />
          <StatCard icon={Car} value={12842} label="Vehicles Detected" color="blue" />
          <StatCard icon={Route} value={18} label="Active Routes" color="blue" />
          <StatCard icon={ShieldAlert} value={3} label="Critical Alerts" color="red" />
        </div>

        {/* Camera grid + Map + Alerts */}
        <div className="grid grid-cols-12 gap-5">
          {/* Camera Grid */}
          <div className="col-span-8">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[13px] font-semibold text-white">
                Live Camera Feeds
              </h3>
              <span className="text-[11px] text-slate-500">
                {cameras.filter((c) => c.status === "online").length} / {cameras.length} online
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {cameras.map((camera) => (
                <CameraCard key={camera.id} camera={camera} />
              ))}
            </div>
          </div>

          {/* Right sidebar — Map + Alerts */}
          <div className="col-span-4 space-y-5">
            {/* Map */}
            <div className="bg-[#111827] border border-white/[0.06] rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.04]">
                <h3 className="text-[13px] font-semibold text-white">
                  Camera Network
                </h3>
              </div>
              <div className="h-[260px]">
                <MapView cameras={cameras} zoom={12} />
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="bg-[#111827] border border-white/[0.06] rounded-xl">
              <div className="px-4 py-3 border-b border-white/[0.04]">
                <h3 className="text-[13px] font-semibold text-white">
                  Recent Alerts
                </h3>
              </div>
              <div className="p-3 space-y-2">
                {recentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-start gap-3 p-2.5 rounded-lg bg-[#0c1017] hover:bg-[#0e1320] transition-colors cursor-pointer"
                    onClick={() => navigate(`/vehicles?search=${alert.vehicleNumber}`)}
                  >
                    <span
                      className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        alert.type === "critical" ? "bg-red-400" : "bg-amber-400"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] font-bold text-white font-mono">
                        {alert.vehicleNumber}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {alert.reason}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {alert.cameraId} · {alert.timeAgo}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="px-4 py-2.5 border-t border-white/[0.04]">
                <button
                  onClick={() => navigate("/alerts")}
                  className="flex items-center gap-1.5 text-[11px] text-blue-400 hover:text-blue-300 font-medium transition-colors"
                >
                  View all alerts
                  <ArrowRight size={12} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
