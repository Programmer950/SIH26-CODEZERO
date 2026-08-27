import { Camera, MapPin, Clock, Percent } from "lucide-react";

export default function VehicleTimeline({ detections, activeStep }) {
  return (
    <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-5">
      <h3 className="text-[13px] font-semibold text-white mb-4 flex items-center gap-2">
        <Camera size={14} className="text-blue-400" />
        VEHICLE MOVEMENT
      </h3>

      <div className="relative">
        {detections.map((detection, index) => {
          const isActive = activeStep === index;
          const isPast = activeStep > index;
          const isLast = index === detections.length - 1;

          return (
            <div key={detection.cameraId + index} className="flex gap-4">
              {/* Timeline line and dot */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 transition-all duration-500 ${
                    isActive
                      ? "bg-blue-600 text-white ring-4 ring-blue-600/20"
                      : isPast
                      ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                      : "bg-[#1e2433] text-slate-500 border border-white/[0.08]"
                  }`}
                >
                  {index + 1}
                </div>
                {!isLast && (
                  <div
                    className={`w-0.5 h-full min-h-[48px] transition-colors duration-500 ${
                      isPast ? "bg-blue-600/30" : "bg-white/[0.06]"
                    }`}
                  />
                )}
              </div>

              {/* Detection info */}
              <div
                className={`pb-6 transition-all duration-500 ${
                  isActive ? "tracking-active" : ""
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[13px] font-bold font-mono ${
                      isActive ? "text-blue-400" : isPast ? "text-blue-400/60" : "text-white"
                    }`}
                  >
                    {detection.cameraId}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[12px] text-slate-400 mb-0.5">
                  <MapPin size={11} />
                  {detection.location}
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="flex items-center gap-1 text-[11px] text-slate-500">
                    <Clock size={10} />
                    {detection.timestamp}
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-slate-500">
                    <Percent size={10} />
                    {detection.confidence}%
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
