import { useState, useEffect } from "react";
import { ShieldAlert, AlertTriangle, Bell, ShieldCheck } from "lucide-react";
import Navbar from "../components/Navbar";
import StatCard from "../components/StatCard";
import AlertCard from "../components/AlertCard";
import MapView from "../components/MapView";
import { getAlerts } from "../services/api";
import { alertStats } from "../data/alerts";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    getAlerts().then(setAlerts);
  }, []);

  const filteredAlerts =
    filter === "all"
      ? alerts
      : alerts.filter((a) => a.type === filter);

  const handleViewMap = (alert) => {
    setSelectedAlert(alert);
  };

  return (
    <div className="flex-1 min-h-screen bg-[#0f1219]">
      <Navbar title="Alerts" />

      <div className="p-6">
        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">Security Alerts</h2>
          <p className="text-[13px] text-slate-400 mt-1">
            Monitor blacklist and watchlist vehicle detections
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard
            icon={ShieldAlert}
            value={alertStats.critical}
            label="Critical"
            color="red"
          />
          <StatCard
            icon={AlertTriangle}
            value={alertStats.warnings}
            label="Warnings"
            color="amber"
          />
          <StatCard
            icon={Bell}
            value={alertStats.totalToday}
            label="Total Today"
            color="blue"
          />
        </div>

        <div className="grid grid-cols-12 gap-5">
          {/* Alert list */}
          <div className="col-span-7">
            {/* Filter tabs */}
            <div className="flex items-center gap-2 mb-4">
              {["all", "critical", "warning"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors ${
                    filter === f
                      ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                      : "text-slate-500 hover:text-slate-300 border border-transparent"
                  }`}
                >
                  {f === "all" ? "All" : f === "critical" ? "Critical" : "Warnings"}
                </button>
              ))}
            </div>

            {filteredAlerts.length === 0 ? (
              <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-12 text-center">
                <ShieldCheck size={40} className="text-slate-600 mx-auto mb-3" />
                <div className="text-[15px] font-semibold text-white mb-1">
                  No active alerts
                </div>
                <div className="text-[13px] text-slate-500">
                  All monitored vehicles are currently normal.
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {filteredAlerts.map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onViewMap={handleViewMap}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Map panel */}
          <div className="col-span-5">
            <div className="bg-[#111827] border border-white/[0.06] rounded-xl overflow-hidden sticky top-20">
              <div className="px-4 py-3 border-b border-white/[0.04]">
                <h3 className="text-[13px] font-semibold text-white">
                  {selectedAlert
                    ? `Detection Location — ${selectedAlert.vehicleNumber}`
                    : "Alert Locations"}
                </h3>
              </div>
              <div className="h-[460px]">
                {selectedAlert ? (
                  <MapView
                    center={[selectedAlert.latitude, selectedAlert.longitude]}
                    zoom={15}
                    route={[
                      {
                        latitude: selectedAlert.latitude,
                        longitude: selectedAlert.longitude,
                        cameraId: selectedAlert.cameraId,
                        timestamp: selectedAlert.timestamp,
                        confidence: selectedAlert.confidence,
                      },
                    ]}
                    vehicleInfo={{ number: selectedAlert.vehicleNumber }}
                  />
                ) : (
                  <MapView
                    route={alerts.map((a) => ({
                      latitude: a.latitude,
                      longitude: a.longitude,
                      cameraId: a.cameraId,
                      timestamp: a.timestamp,
                      confidence: a.confidence,
                    }))}
                    zoom={12}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
