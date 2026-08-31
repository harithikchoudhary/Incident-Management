import { NavLink } from "react-router-dom";
import {
  MessageSquare,
  LayoutDashboard,
  ClipboardList,
  Search,
  DownloadCloud,
  ShieldCheck,
  Wifi,
  WifiOff,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Incident Chat", icon: MessageSquare, end: true },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/incidents", label: "Historical Incidents", icon: ClipboardList },
  { to: "/search", label: "Search & Details", icon: Search },
  { to: "/ingestion", label: "Data Ingestion", icon: DownloadCloud },
];

export default function Sidebar({ health }) {
  return (
    <aside className="flex h-full w-64 flex-shrink-0 flex-col bg-slate-900 text-slate-300">
      <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold leading-tight text-white">Incident</h1>
          <p className="text-xs text-slate-400">Management Platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? "bg-brand-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-800 px-5 py-4">
        <div className="flex items-center gap-2">
          {health === "connected" ? (
            <>
              <Wifi className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">Backend Connected</span>
            </>
          ) : health === "disconnected" ? (
            <>
              <WifiOff className="h-4 w-4 text-red-400" />
              <span className="text-xs font-medium text-red-400">Backend Disconnected</span>
            </>
          ) : (
            <>
              <span className="h-4 w-4 animate-pulse rounded-full bg-slate-600" />
              <span className="text-xs font-medium text-slate-500">Checking…</span>
            </>
          )}
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
          AI-Powered Incident Management
        </p>
      </div>
    </aside>
  );
}
