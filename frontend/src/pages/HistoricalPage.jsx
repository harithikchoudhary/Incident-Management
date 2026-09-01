import { useEffect, useMemo, useState } from "react";
import { RefreshCw, ChevronDown, SlidersHorizontal, Inbox } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { SeverityBadge, StatusBadge, Spinner } from "../components/ui.jsx";

function IncidentRow({ inc }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr
        onClick={() => setOpen((o) => !o)}
        className="cursor-pointer border-t border-slate-100 transition hover:bg-slate-50"
      >
        <td className="px-4 py-3">
          <SeverityBadge severity={inc.severity} />
        </td>
        <td className="whitespace-nowrap px-4 py-3 font-mono text-sm font-semibold text-brand-700">
          {inc.incident_id}
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-600">
          {inc.application}
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
          {inc.lob ? (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">
              {inc.lob}
            </span>
          ) : (
            <span className="text-xs text-slate-300">—</span>
          )}
        </td>
        <td
          className="max-w-md truncate px-4 py-3 text-sm text-slate-600"
          title={inc.problem_summary}
        >
          {inc.problem_summary}
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={inc.status} />
        </td>
        <td className="px-4 py-3 text-right">
          <ChevronDown
            className={`inline h-4 w-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
          />
        </td>
      </tr>

      {open && (
        <tr className="border-t border-slate-100 bg-slate-50/60">
          <td colSpan={7} className="px-4 py-4">
            <div className="animate-fade-in space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Meta label="Application" value={inc.application} />
                <Meta label="Environment" value={inc.environment} />
                <Meta label="Severity" value={inc.severity} />
                <Meta label="Status" value={inc.status} />
              </div>

              <IntakeDetails inc={inc} />

              <Section title="Problem">{inc.problem_summary}</Section>

              {inc.root_cause && (
                <div>
                  <p className="label">Root Cause</p>
                  <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-slate-700">{inc.root_cause}</p>
                </div>
              )}

              {inc.resolution?.length > 0 && (
                <div>
                  <p className="label">Resolution Steps</p>
                  <ol className="space-y-1.5">
                    {inc.resolution.map((step, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-700">
                        <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">
                          {i + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {inc.symptoms?.length > 0 && (
                <Section title="Symptoms">{inc.symptoms.join(", ")}</Section>
              )}

              {inc.error_codes?.length > 0 && (
                <div>
                  <p className="label">Error Codes</p>
                  <div className="flex flex-wrap gap-1.5">
                    {inc.error_codes.map((e) => (
                      <code key={e} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                        {e}
                      </code>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between border-t border-slate-100 pt-3">
                {inc.created_at && (
                  <span className="text-xs text-slate-400">Created: {inc.created_at}</span>
                )}
                <Link
                  to={`/search?id=${encodeURIComponent(inc.incident_id)}`}
                  className="text-xs font-semibold text-brand-600 hover:text-brand-700"
                >
                  View full details →
                </Link>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function Meta({ label, value }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="text-sm font-medium text-slate-700">{value}</p>
    </div>
  );
}

function IntakeDetails({ inc }) {
  const rows = [
    { label: "LOB Impacted", value: inc.lob },
    { label: "Identified At", value: inc.identified_time },
    { label: "Impacted Users", value: inc.impacted_users },
    { label: "Stuck / Failed Cases", value: inc.failed_cases },
    { label: "Upstream / Downstream", value: inc.upstream_downstream },
    { label: "Business Impact", value: inc.business_impact },
  ].filter((r) => r.value);

  if (rows.length === 0 && !inc.issue) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="label mb-2">Incident Intake Details</p>
      {inc.issue && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-slate-400">Issue</p>
          <p className="text-sm text-slate-700">{inc.issue}</p>
        </div>
      )}
      {rows.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {rows.map((r) => (
            <div key={r.label}>
              <p className="text-xs font-semibold text-slate-400">{r.label}</p>
              <p className="text-sm text-slate-700">{r.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <p className="label">{title}</p>
      <p className="text-sm text-slate-700">{children}</p>
    </div>
  );
}

export default function HistoricalPage() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [app, setApp] = useState("All");
  const [sev, setSev] = useState("All");
  const [status, setStatus] = useState("All");
  const [lob, setLob] = useState("All");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listIncidents();
      setIncidents(data.incidents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const apps = useMemo(
    () => ["All", ...[...new Set(incidents.map((i) => i.application))].sort()],
    [incidents]
  );
  const statuses = useMemo(
    () => ["All", ...[...new Set(incidents.map((i) => i.status))].sort()],
    [incidents]
  );
  const lobs = useMemo(
    () => [
      "All",
      ...[...new Set(incidents.map((i) => i.lob).filter(Boolean))].sort(),
    ],
    [incidents]
  );

  const filtered = incidents.filter(
    (i) =>
      (app === "All" || i.application === app) &&
      (sev === "All" || i.severity === sev) &&
      (status === "All" || i.status === status) &&
      (lob === "All" || i.lob === lob)
  );

  return (
    <div className="px-8 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Historical Incidents</h2>
          <p className="text-sm text-slate-500">Browse and filter the extracted incident knowledge base.</p>
        </div>
        <button className="btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      <div className="card mb-5 flex flex-wrap items-end gap-4 p-4">
        <div className="flex items-center gap-2 text-slate-500">
          <SlidersHorizontal className="h-4 w-4" />
          <span className="text-sm font-semibold">Filters</span>
        </div>
        <Select label="Application" value={app} onChange={setApp} options={apps} />
        <Select label="LOB" value={lob} onChange={setLob} options={lobs} />
        <Select label="Severity" value={sev} onChange={setSev} options={["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]} />
        <Select label="Status" value={status} onChange={setStatus} options={statuses} />
        <span className="ml-auto text-sm text-slate-500">
          Showing {filtered.length} of {incidents.length}
        </span>
      </div>

      {loading && incidents.length === 0 ? (
        <div className="flex items-center gap-2 text-slate-500">
          <Spinner className="h-5 w-5" /> Loading incidents…
        </div>
      ) : error ? (
        <div className="card border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center gap-2 p-12 text-center text-slate-500">
          <Inbox className="h-10 w-10 text-slate-300" />
          <p className="font-medium">No incidents found</p>
          <p className="text-sm">
            Go to{" "}
            <Link to="/ingestion" className="font-semibold text-brand-600">
              Data Ingestion
            </Link>{" "}
            to load mock data.
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="scroll-brand overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-left">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Incident ID</th>
                  <th className="px-4 py-3">Application</th>
                  <th className="px-4 py-3">LOB</th>
                  <th className="px-4 py-3">Problem Summary</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => (
                  <IncidentRow key={inc.incident_id} inc={inc} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <div>
      <label className="label">{label}</label>
      <select className="input w-44" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
