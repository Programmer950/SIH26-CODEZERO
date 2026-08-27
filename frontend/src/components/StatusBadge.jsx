import { ShieldAlert, AlertTriangle, CheckCircle, Info } from "lucide-react";

const statusConfig = {
  normal: {
    label: "Normal",
    icon: CheckCircle,
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  blacklisted: {
    label: "Blacklisted",
    icon: ShieldAlert,
    className: "bg-red-500/10 text-red-400 border-red-500/20",
  },
  watchlist: {
    label: "Watchlist",
    icon: AlertTriangle,
    className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  online: {
    label: "Online",
    icon: CheckCircle,
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  offline: {
    label: "Offline",
    icon: Info,
    className: "bg-red-500/10 text-red-400 border-red-500/20",
  },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || statusConfig.normal;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border ${config.className}`}
    >
      <Icon size={12} />
      {config.label}
    </span>
  );
}
