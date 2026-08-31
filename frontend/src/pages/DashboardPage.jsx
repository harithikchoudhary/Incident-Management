import { useEffect, useMemo, useState } from "react";
import { RefreshCw, AlertTriangle, CheckCircle2, Boxes, Activity, Server, CalendarDays, PieChart as PieIcon } from "lucide-react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { api } from "../api/client.js";
import MetricCard from "../components/MetricCard.jsx";
import { Spinner } from "../components/ui.jsx";

const SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const SEVERITY_COLORS = {
  CRITICAL: "#dc2626",
  HIGH: "#f97316",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
};

function normalizeSeverity(sev) {
  const up = (sev || "").toUpperCase();
  return SEVERITY_ORDER.includes(up) ? up : "MEDIUM";
}

function buildMonthly(incidents) {
  const map = new Map();
  for (const inc of incidents) {
    const d = new Date(inc.created_at);
    if (Number.isNaN(d.getTime())) continue;
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    map.set(key, (map.get(key) || 0) + 1);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([key, count]) => {
      const [y, m] = key.split("-");
      const label = new Date(Number(y), Number(m) - 1).toLocaleString("en", {
        month: "short",
        year: "2-digit",
      });
      return { month: label, count };
    });
}

function buildSeverity(incidents) {
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const inc of incidents) counts[normalizeSeverity(inc.severity)] += 1;
  return SEVERITY_ORDER.map((sev) => ({ name: sev, value: counts[sev] })).filter((d) => d.value > 0);
}

function buildLast7Days(incidents) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = [];
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    days.push({
      key: d.toDateString(),
      label: d.toLocaleDateString("en", { weekday: "short", day: "numeric" }),
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
    });
  }
  const dayMap = new Map(days.map((d) => [d.key, d]));
  for (const inc of incidents) {
    const d = new Date(inc.created_at);
    if (Number.isNaN(d.getTime())) continue;
    d.setHours(0, 0, 0, 0);
    const bucket = dayMap.get(d.toDateString());
    if (bucket) bucket[normalizeSeverity(inc.severity)] += 1;
  }
  return days;
}

const tooltipStyle = {
  borderRadius: "0.5rem",
  border: "1px solid #e2e8f0",
  fontSize: "0.8rem",
  boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
};

function ChartCard({ title, icon: Icon, children, empty, emptyText }) {
  return (
    <div className="card p-5">
      <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-800">
        {Icon && <Icon className="h-4 w-4 text-brand-600" />} {title}
      </h3>
      {empty ? <p className="py-12 text-center text-sm text-slate-500">{emptyText}</p> : children}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, list] = await Promise.all([api.dashboard(), api.listIncidents()]);
      setData(dashboard);
      setIncidents(list.incidents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const monthly = useMemo(() => buildMonthly(incidents), [incidents]);
  const severity = useMemo(() => buildSeverity(incidents), [incidents]);
  const last7 = useMemo(() => buildLast7Days(incidents), [incidents]);
  const last7Total = useMemo(
    () => last7.reduce((sum, d) => sum + d.CRITICAL + d.HIGH + d.MEDIUM + d.LOW, 0),
    [last7],
  );

  const maxCause = data?.top_root_causes?.reduce((m, c) => Math.max(m, c.count), 0) || 1;

  return (
    <div className="px-8 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-sm text-slate-500">Overview of the incident knowledge base.</p>
        </div>
        <button className="btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {loading && !data ? (
        <div className="flex items-center gap-2 text-slate-500">
          <Spinner className="h-5 w-5" /> Loading dashboard…
        </div>
      ) : error ? (
        <div className="card border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      ) : (
        data && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Total Incidents" value={data.total_incidents} icon={Boxes} accent="brand" />
              <MetricCard label="Resolved" value={data.resolved_incidents} icon={CheckCircle2} accent="emerald" />
              <MetricCard
                label="Applications"
                value={data.applications_affected.length}
                icon={Server}
                accent="amber"
              />
              <MetricCard label="High Severity" value={data.high_severity_count} icon={AlertTriangle} accent="red" />
            </div>

            {data.total_incidents === 0 && (
              <div className="card flex items-center gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                <span>
                  No incidents in the system yet. Head to{" "}
                  <Link to="/ingestion" className="font-semibold underline">
                    Data Ingestion
                  </Link>{" "}
                  to load mock data.
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <ChartCard
                  title="Incidents per Month"
                  icon={CalendarDays}
                  empty={monthly.length === 0}
                  emptyText="No dated incidents to chart yet."
                >
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={monthly} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#f8fafc" }} />
                      <Bar dataKey="count" name="Incidents" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={48} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              <ChartCard
                title="Severity Distribution"
                icon={PieIcon}
                empty={severity.length === 0}
                emptyText="No severity data yet."
              >
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={severity}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {severity.map((entry) => (
                        <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: "0.8rem", color: "#475569" }} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            <ChartCard
              title="Last 7 Days by Severity"
              icon={Activity}
              empty={last7Total === 0}
              emptyText="No incidents recorded in the last 7 days."
            >
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={last7} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#f8fafc" }} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: "0.8rem", color: "#475569" }} />
                  {SEVERITY_ORDER.map((sev, idx) => (
                    <Bar
                      key={sev}
                      dataKey={sev}
                      stackId="sev"
                      name={sev.charAt(0) + sev.slice(1).toLowerCase()}
                      fill={SEVERITY_COLORS[sev]}
                      radius={idx === SEVERITY_ORDER.length - 1 ? [6, 6, 0, 0] : [0, 0, 0, 0]}
                      maxBarSize={48}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="card p-5">
                <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-800">
                  <Server className="h-4 w-4 text-brand-600" /> Applications Affected
                </h3>
                {data.applications_affected.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {[...data.applications_affected].sort().map((app) => (
                      <span
                        key={app}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700"
                      >
                        {app}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No applications affected yet.</p>
                )}
              </div>

              <div className="card p-5">
                <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-800">
                  <Activity className="h-4 w-4 text-brand-600" /> Top Root Causes
                </h3>
                {data.top_root_causes.length > 0 ? (
                  <div className="space-y-3">
                    {data.top_root_causes.map((rc) => (
                      <div key={rc.cause}>
                        <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-slate-700" title={rc.cause}>
                            {rc.cause}
                          </span>
                          <span className="flex-shrink-0 font-semibold text-slate-500">{rc.count}</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-brand-500"
                            style={{ width: `${(rc.count / maxCause) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No root causes found yet.</p>
                )}
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
