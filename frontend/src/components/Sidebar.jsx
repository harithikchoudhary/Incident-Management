import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  MessageSquare,
  LayoutDashboard,
  ClipboardList,
  Search,
  DownloadCloud,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Incident Chat", icon: MessageSquare, end: true },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/incidents", label: "Historical Incidents", icon: ClipboardList },
  { to: "/search", label: "Search & Details", icon: Search },
  { to: "/ingestion", label: "Data Ingestion", icon: DownloadCloud },
];

/** Faithful vector recreation of the L&T Finance mark - used until /logo.png is provided. */
function LogoGlyph({ className }) {
  return (
    <svg viewBox="0 0 40 40" className={className} role="img" aria-label="L&T Finance">
      <rect width="40" height="40" rx="8" fill="#FDB913" />
      <path d="M11 9h4v16h9v4H11z" fill="#0d0e11" />
      <path
        d="M4 30l10-5h22l-6 5z"
        fill="#1a8bc7"
      />
    </svg>
  );
}

function BrandLogo({ imgFailed, setImgFailed }) {
  if (imgFailed) {
    return (
      <div className="flex items-center gap-3">
        <LogoGlyph className="h-10 w-10 flex-shrink-0" />
        <div className="min-w-0">
          <h1 className="truncate text-sm font-bold leading-tight text-ink-800">L&amp;T Finance</h1>
          <p className="truncate text-xs text-ink-400">Incident Management</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <img
        src="/download.jpg"
        alt="L&T Finance"
        className="h-9 w-auto max-w-full rounded-md object-contain"
        onError={() => setImgFailed(true)}
      />
      <p className="mt-1.5 truncate text-xs text-ink-400">Incident Management</p>
    </div>
  );
}

export default function Sidebar({ health, open, onClose }) {
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-ink-900/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-full w-72 max-w-[85vw] flex-shrink-0 transform flex-col border-r border-ink-100 bg-white text-ink-700 transition-transform duration-200 ease-out lg:static lg:z-auto lg:w-64 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 border-b border-ink-100 px-5 py-5">
          <BrandLogo imgFailed={imgFailed} setImgFailed={setImgFailed} />
          <button
            className="ml-auto rounded-lg p-1.5 text-ink-400 hover:bg-ink-50 hover:text-ink-700 lg:hidden"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="scroll-light flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-400 text-ink-900 shadow-sm"
                    : "text-ink-600 hover:bg-brand-50 hover:text-ink-900"
                }`
              }
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span className="truncate">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-ink-100 px-5 py-4">
          <div className="flex items-center gap-2">
            {health === "connected" ? (
              <>
                <Wifi className="h-4 w-4 text-emerald-500" />
                <span className="text-xs font-medium text-emerald-600">Backend Connected</span>
              </>
            ) : health === "disconnected" ? (
              <>
                <WifiOff className="h-4 w-4 text-red-500" />
                <span className="text-xs font-medium text-red-600">Backend Disconnected</span>
              </>
            ) : (
              <>
                <span className="h-4 w-4 animate-pulse rounded-full bg-ink-200" />
                <span className="text-xs font-medium text-ink-400">Checking…</span>
              </>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-ink-400">
            AI-Powered Incident Management
          </p>
        </div>
      </aside>
    </>
  );
}
