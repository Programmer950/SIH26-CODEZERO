import { Video, WifiOff, Car } from "lucide-react";

export default function CameraCard({ camera }) {
  const isOnline = camera.status === "online";

  return (
    <div className="bg-[#111827] border border-white/[0.06] rounded-xl overflow-hidden">
      {/* Camera Feed Placeholder */}
      <div className="camera-feed h-36 flex items-center justify-center relative">
        {isOnline ? (
          <>
            {/* Simulated camera feed with vehicle icons */}
            <div className="flex items-end gap-3 opacity-30">
              <Car size={28} className="text-slate-500" />
              <Car size={22} className="text-slate-500 mb-0.5" />
              <Car size={32} className="text-slate-500" />
            </div>
            {/* Live badge */}
            <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-red-600/90 px-2 py-0.5 rounded text-[10px] font-semibold text-white">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot" />
              LIVE
            </div>
            {/* Camera ID badge */}
            <div className="absolute top-3 right-3 bg-black/50 px-2 py-0.5 rounded text-[10px] font-mono text-slate-300">
              {camera.id}
            </div>
            {/* Timestamp */}
            <div className="absolute bottom-2 right-3 text-[10px] font-mono text-slate-500">
              {camera.lastDetection}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-600">
            <WifiOff size={28} />
            <span className="text-[11px] font-medium">Camera Offline</span>
            <span className="text-[10px] text-slate-600">
              Last seen {camera.lastDetection}
            </span>
          </div>
        )}
      </div>

      {/* Camera Info */}
      <div className="p-3 border-t border-white/[0.04]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[12px] font-semibold text-white">
            {camera.id}
          </span>
          <span
            className={`flex items-center gap-1 text-[10px] font-medium ${
              isOnline ? "text-emerald-400" : "text-red-400"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOnline ? "bg-emerald-400" : "bg-red-400"
              }`}
            />
            {isOnline ? "Online" : "Offline"}
          </span>
        </div>
        <div className="text-[11px] text-slate-400">{camera.name}</div>
        {isOnline && (
          <div className="flex items-center gap-1 mt-2 text-[11px] text-slate-500">
            <Video size={12} />
            <span>{camera.vehiclesDetected} vehicles detected</span>
          </div>
        )}
      </div>
    </div>
  );
}
