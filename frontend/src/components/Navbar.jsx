import { Bell } from "lucide-react";

export default function Navbar({ title }) {
  return (
    <header className="h-14 bg-[#0c1017]/80 backdrop-blur-sm border-b border-white/[0.06] flex items-center justify-between px-6 sticky top-0 z-40">
      <h1 className="text-[15px] font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2 text-[12px] text-emerald-400 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          System Online
        </div>
        <button className="relative text-slate-400 hover:text-white transition-colors">
          <Bell size={18} />
          <span className="absolute -top-1 -right-1.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
            3
          </span>
        </button>
      </div>
    </header>
  );
}
