import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Car,
  Map,
  ShieldAlert,
  Radio,
  Camera,
} from "lucide-react";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/vehicles", label: "Vehicle Tracking", icon: Car },
  { path: "/traffic", label: "Traffic Heatmap", icon: Map },
  { path: "/alerts", label: "Alerts", icon: ShieldAlert },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-60 bg-[#0c1017] border-r border-white/[0.06] flex flex-col h-screen sticky top-0 shrink-0">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <Camera size={16} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-bold tracking-wider text-white leading-tight">
              VEHICLE
            </div>
            <div className="text-[13px] font-bold tracking-wider text-blue-400 leading-tight">
              INTELLIGENCE
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = location.pathname === path;
          return (
            <NavLink
              key={path}
              to={path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${
                isActive
                  ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
              }`}
            >
              <Icon size={18} strokeWidth={isActive ? 2 : 1.5} />
              {label}
            </NavLink>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="px-4 py-4 border-t border-white/[0.06]">
        <div className="text-[10px] font-semibold tracking-widest text-slate-500 mb-3">
          SYSTEM STATUS
        </div>
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 text-[12px] text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
            AI Engine Online
          </div>
          <div className="flex items-center gap-2 text-[12px] text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
            <span className="flex items-center gap-1">
              <Radio size={11} />
              24 Cameras Connected
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
