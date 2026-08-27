import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import { MapPin, Clock, Eye, Percent } from "lucide-react";

export default function AlertCard({ alert, onViewMap }) {
  const navigate = useNavigate();
  const isCritical = alert.type === "critical";

  const handleViewVehicle = () => {
    navigate(`/vehicles?search=${alert.vehicleNumber}`);
  };

  return (
    <div
      className={`bg-[#111827] border rounded-xl p-4 ${
        isCritical
          ? "border-red-500/20"
          : "border-amber-500/15"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <StatusBadge status={isCritical ? "blacklisted" : "watchlist"} />
        <span className="text-[10px] text-slate-500">{alert.timeAgo}</span>
      </div>

      {/* Vehicle number */}
      <div className="text-[15px] font-bold text-white font-mono tracking-wider mb-1">
        {alert.vehicleNumber}
      </div>
      <div className="text-[12px] text-slate-400 mb-3">{alert.reason}</div>

      {/* Detection info */}
      <div className="space-y-1.5 mb-4">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <MapPin size={11} />
          {alert.cameraId} · {alert.location}
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <Clock size={11} />
            {alert.timestamp}
          </span>
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <Percent size={11} />
            {alert.confidence}%
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleViewVehicle}
          className="flex items-center gap-1.5 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-[11px] font-medium px-3 py-1.5 rounded-md transition-colors"
        >
          <Eye size={12} />
          View Vehicle
        </button>
        <button
          onClick={() => onViewMap && onViewMap(alert)}
          className="flex items-center gap-1.5 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-[11px] font-medium px-3 py-1.5 rounded-md transition-colors"
        >
          <MapPin size={12} />
          View on Map
        </button>
      </div>
    </div>
  );
}
