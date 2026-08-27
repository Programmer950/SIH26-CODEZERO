import StatusBadge from "./StatusBadge";
import { Car, Clock, Eye, Hash } from "lucide-react";

export default function VehicleCard({ vehicle }) {
  const firstDetection = vehicle.detections[0];
  const lastDetection = vehicle.detections[vehicle.detections.length - 1];

  return (
    <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-5">
      {/* Vehicle header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-lg font-bold text-white font-mono tracking-wider">
            {vehicle.number}
          </div>
          <div className="text-[13px] text-slate-400 mt-0.5">
            {vehicle.color} {vehicle.type}
          </div>
        </div>
        <StatusBadge status={vehicle.status} />
      </div>

      {/* Vehicle details grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0c1017] rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
            <Clock size={11} />
            First Seen
          </div>
          <div className="text-[13px] text-white font-mono">
            {firstDetection.timestamp}
          </div>
        </div>
        <div className="bg-[#0c1017] rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
            <Clock size={11} />
            Last Seen
          </div>
          <div className="text-[13px] text-white font-mono">
            {lastDetection.timestamp}
          </div>
        </div>
        <div className="bg-[#0c1017] rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
            <Eye size={11} />
            Detections
          </div>
          <div className="text-[13px] text-white font-mono">
            {vehicle.detections.length}
          </div>
        </div>
        <div className="bg-[#0c1017] rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
            <Hash size={11} />
            Status
          </div>
          <div className="text-[13px] text-white capitalize">
            {vehicle.status}
          </div>
        </div>
      </div>

      {/* Route summary */}
      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-2">
          <Car size={11} />
          ROUTE
        </div>
        <div className="flex items-center gap-2 text-[12px] font-mono">
          {vehicle.detections.map((d, i) => (
            <span key={d.cameraId} className="flex items-center gap-2">
              <span className="text-blue-400">{d.cameraId}</span>
              {i < vehicle.detections.length - 1 && (
                <span className="text-slate-600">→</span>
              )}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
