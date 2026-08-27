import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { Play, Square, SearchX } from "lucide-react";
import Navbar from "../components/Navbar";
import SearchBar from "../components/SearchBar";
import VehicleCard from "../components/VehicleCard";
import VehicleTimeline from "../components/VehicleTimeline";
import MapView from "../components/MapView";
import { searchVehicle } from "../services/api";

export default function Vehicles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [vehicle, setVehicle] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [activeStep, setActiveStep] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);

  // Handle URL search param (from alert "View Vehicle" links)
  useEffect(() => {
    const q = searchParams.get("search");
    if (q) {
      handleSearch(q);
    }
  }, [searchParams]);

  const handleSearch = async (query) => {
    setSearchedQuery(query);
    setActiveStep(-1);
    setIsPlaying(false);
    const result = await searchVehicle(query);
    if (result) {
      setVehicle(result);
      setNotFound(false);
    } else {
      setVehicle(null);
      setNotFound(true);
    }
    // Clear the URL param to avoid re-triggering
    setSearchParams({});
  };

  const playTracking = useCallback(() => {
    if (!vehicle || isPlaying) return;
    setIsPlaying(true);
    setActiveStep(0);

    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step >= vehicle.detections.length) {
        clearInterval(interval);
        setIsPlaying(false);
      } else {
        setActiveStep(step);
      }
    }, 1500);
  }, [vehicle, isPlaying]);

  const stopTracking = () => {
    setIsPlaying(false);
    setActiveStep(-1);
  };

  return (
    <div className="flex-1 min-h-screen bg-[#0f1219]">
      <Navbar title="Vehicle Tracking" />

      <div className="p-6">
        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">Vehicle Tracking</h2>
          <p className="text-[13px] text-slate-400 mt-1">
            Search and reconstruct vehicle movement across cameras
          </p>
        </div>

        {/* Search */}
        <div className="max-w-2xl mb-6">
          <SearchBar onSearch={handleSearch} />
          <div className="mt-2 text-[11px] text-slate-600">
            Try: TN09AB1234 · TN09XY7788 · TN10AB1234
          </div>
        </div>

        {/* Not found state */}
        {notFound && (
          <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-12 text-center">
            <SearchX size={40} className="text-slate-600 mx-auto mb-3" />
            <div className="text-[15px] font-semibold text-white mb-1">
              No vehicle found
            </div>
            <div className="text-[13px] text-slate-500">
              No detections were found for{" "}
              <span className="font-mono text-slate-400">{searchedQuery}</span>.
            </div>
          </div>
        )}

        {/* Vehicle results */}
        {vehicle && (
          <div className="grid grid-cols-12 gap-5">
            {/* Left column — Vehicle info + Timeline */}
            <div className="col-span-4 space-y-5">
              <VehicleCard vehicle={vehicle} />

              {/* Demo mode button */}
              <div className="flex gap-2">
                {!isPlaying ? (
                  <button
                    onClick={playTracking}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-[12px] font-medium px-4 py-2 rounded-lg transition-colors"
                  >
                    <Play size={14} />
                    Play Tracking
                  </button>
                ) : (
                  <button
                    onClick={stopTracking}
                    className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-[12px] font-medium px-4 py-2 rounded-lg transition-colors"
                  >
                    <Square size={14} />
                    Stop
                  </button>
                )}
              </div>

              <VehicleTimeline
                detections={vehicle.detections}
                activeStep={activeStep}
              />
            </div>

            {/* Right column — Route Map */}
            <div className="col-span-8">
              <div className="bg-[#111827] border border-white/[0.06] rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
                  <h3 className="text-[13px] font-semibold text-white">
                    Vehicle Route
                  </h3>
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                    {vehicle.detections.map((d, i) => (
                      <span key={d.cameraId} className="flex items-center gap-2">
                        <span
                          className={
                            activeStep === i
                              ? "text-blue-400 font-bold"
                              : "text-slate-500"
                          }
                        >
                          {d.cameraId}
                        </span>
                        {i < vehicle.detections.length - 1 && (
                          <span className="text-slate-700">→</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="h-[520px]">
                  <MapView
                    route={vehicle.detections}
                    activeRouteStep={activeStep}
                    vehicleInfo={vehicle}
                    center={[
                      vehicle.detections.reduce((sum, d) => sum + d.latitude, 0) /
                        vehicle.detections.length,
                      vehicle.detections.reduce((sum, d) => sum + d.longitude, 0) /
                        vehicle.detections.length,
                    ]}
                    zoom={13}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
