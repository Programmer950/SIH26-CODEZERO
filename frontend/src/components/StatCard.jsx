export default function StatCard({ icon: Icon, value, label, trend, color = "blue" }) {
  const colorMap = {
    blue: "text-blue-400 bg-blue-500/10",
    green: "text-emerald-400 bg-emerald-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    red: "text-red-400 bg-red-500/10",
  };

  const iconColors = colorMap[color] || colorMap.blue;

  return (
    <div className="bg-[#111827] border border-white/[0.06] rounded-xl p-4 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${iconColors}`}>
        <Icon size={20} />
      </div>
      <div>
        <div className="text-2xl font-bold text-white leading-none">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
        <div className="text-[12px] text-slate-400 mt-1">{label}</div>
        {trend && (
          <div className="text-[11px] text-emerald-400 mt-1">{trend}</div>
        )}
      </div>
    </div>
  );
}
