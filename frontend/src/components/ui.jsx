// Small presentational helpers shared across pages.
import { Loader2 } from "lucide-react";

const SEVERITY_STYLES = {
  CRITICAL: "bg-red-100 text-red-700 ring-red-600/20",
  HIGH: "bg-orange-100 text-orange-700 ring-orange-600/20",
  MEDIUM: "bg-amber-100 text-amber-700 ring-amber-600/20",
  LOW: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
};

const SEVERITY_DOT = {
  CRITICAL: "bg-red-500",
  HIGH: "bg-orange-500",
  MEDIUM: "bg-amber-500",
  LOW: "bg-emerald-500",
};

export function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || "bg-slate-100 text-slate-600 ring-slate-500/20";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${style}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[severity] || "bg-slate-400"}`} />
      {severity || "UNKNOWN"}
    </span>
  );
}

export function StatusBadge({ status }) {
  const resolved = status === "RESOLVED";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${
        resolved
          ? "bg-emerald-100 text-emerald-700 ring-emerald-600/20"
          : "bg-blue-100 text-blue-700 ring-blue-600/20"
      }`}
    >
      {status || "UNKNOWN"}
    </span>
  );
}

export function Spinner({ className = "" }) {
  return <Loader2 className={`animate-spin ${className}`} />;
}

export function Pill({ children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 ${className}`}
    >
      {children}
    </span>
  );
}
