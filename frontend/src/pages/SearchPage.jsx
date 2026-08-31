import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, FileText, RotateCcw, MessageCircle, AlertCircle } from "lucide-react";
import { api } from "../api/client.js";
import { SeverityBadge, StatusBadge, Spinner } from "../components/ui.jsx";
import { ChatConversation } from "../components/ChatConversation.jsx";

function looksLikeId(q) {
  const s = q.trim().toUpperCase();
  return s.startsWith("INC") || s.slice(0, 10).includes("-");
}

function IncidentDetail({ data }) {
  const [conversation, setConversation] = useState(null);
  const [loadingConv, setLoadingConv] = useState(false);
  const [convError, setConvError] = useState(null);

  const loadConversation = async () => {
    setLoadingConv(true);
    setConvError(null);
    try {
      const res = await api.getConversation(data.incident_id);
      setConversation(res.conversation || "");
    } catch (err) {
      setConvError(err.message);
    } finally {
      setLoadingConv(false);
    }
  };

  return (
    <div className="card animate-fade-in overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50 px-6 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <SeverityBadge severity={data.severity} />
          <h3 className="font-mono text-lg font-bold text-slate-900">{data.incident_id}</h3>
          <span className="text-slate-400">•</span>
          <span className="font-semibold text-slate-700">{data.application}</span>
          <StatusBadge status={data.status} />
        </div>
      </div>

      <div className="space-y-5 p-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Meta label="Environment" value={data.environment} />
          <Meta label="Severity" value={data.severity} />
          <Meta label="Status" value={data.status} />
          <Meta label="Created" value={data.created_at || "N/A"} />
          <Meta label="Resolved" value={data.resolved_at || "N/A"} />
        </div>

        <Divider />

        <div>
          <p className="label">Problem</p>
          <p className="text-sm text-slate-700">{data.problem_summary}</p>
        </div>

        <IntakeDetails data={data} />

        {data.symptoms?.length > 0 && (
          <div>
            <p className="label">Symptoms</p>
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
              {data.symptoms.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        {data.error_codes?.length > 0 && (
          <div>
            <p className="label">Error Codes</p>
            <div className="flex flex-wrap gap-1.5">
              {data.error_codes.map((e) => (
                <code key={e} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                  {e}
                </code>
              ))}
            </div>
          </div>
        )}

        {data.root_cause && (
          <div>
            <p className="label">Root Cause</p>
            <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-slate-700">{data.root_cause}</p>
          </div>
        )}

        {data.resolution?.length > 0 && (
          <div>
            <p className="label">Resolution Steps</p>
            <ol className="space-y-1.5">
              {data.resolution.map((step, i) => (
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

        <Divider />

        <div>
          <div className="mb-3 flex items-center justify-between">
            <p className="flex items-center gap-2 font-semibold text-slate-800">
              <MessageCircle className="h-4 w-4 text-brand-600" /> Original Google Chat Conversation
            </p>
            {conversation === null && (
              <button className="btn-secondary" onClick={loadConversation} disabled={loadingConv}>
                {loadingConv ? <Spinner className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                Load Conversation
              </button>
            )}
          </div>

          {convError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {convError}
            </div>
          )}

          {conversation !== null && (
            <div className="animate-fade-in">
              {conversation.trim() === "" ? (
                <p className="text-sm text-slate-500">No conversation data available.</p>
              ) : (
                <ChatConversation text={conversation} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
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

function IntakeDetails({ data }) {
  const rows = [
    { label: "LOB Impacted", value: data.lob },
    { label: "Identified At", value: data.identified_time },
    { label: "Impacted Users", value: data.impacted_users },
    { label: "Stuck / Failed Cases", value: data.failed_cases },
    { label: "Upstream / Downstream", value: data.upstream_downstream },
    { label: "Business Impact", value: data.business_impact },
  ].filter((r) => r.value);

  if (rows.length === 0 && !data.issue) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="label mb-2">Incident Intake Details</p>
      {data.issue && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-slate-400">Issue</p>
          <p className="text-sm text-slate-700">{data.issue}</p>
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

function Divider() {
  return <div className="h-px bg-slate-100" />;
}

function ResultCard({ result, onOpen }) {
  const inc = result.incident;
  const pct = Math.round((result.score ?? 0) * 100);
  return (
    <div className="card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <SeverityBadge severity={inc.severity} />
        <span className="font-mono text-sm font-semibold text-brand-700">{inc.incident_id}</span>
        <span className="text-sm font-medium text-slate-500">{inc.application}</span>
        <span className="ml-auto rounded bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
          {pct}% match
        </span>
      </div>
      <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      <p className="mb-3 text-sm text-slate-600">{inc.problem_summary}</p>
      {inc.root_cause && (
        <p className="mb-3 text-sm text-slate-600">
          <span className="font-semibold text-slate-700">Root cause:</span> {inc.root_cause}
        </p>
      )}
      <button className="text-xs font-semibold text-brand-600 hover:text-brand-700" onClick={() => onOpen(inc)}>
        View full details →
      </button>
    </div>
  );
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [appFilter, setAppFilter] = useState("");
  const [detail, setDetail] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const runSearch = useCallback(async (q, application) => {
    const text = q.trim();
    if (!text) {
      setMessage("Please enter a search query or incident ID.");
      return;
    }
    setLoading(true);
    setMessage(null);
    setResults(null);
    setDetail(null);

    try {
      if (looksLikeId(text)) {
        try {
          const data = await api.getIncident(text);
          setDetail(data);
        } catch (err) {
          if (err.status === 404) {
            setMessage(`Incident "${text}" not found. Try searching by description instead.`);
          } else {
            throw err;
          }
        }
      } else {
        const res = await api.searchIncidents(text, application);
        if (res.results?.length) {
          setResults(res);
        } else {
          setMessage("No matching incidents found. Try different search terms.");
        }
      }
    } catch (err) {
      setMessage(err.message || "Search failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Deep link support: /search?id=INC-XXXX from other pages
  useEffect(() => {
    const id = searchParams.get("id");
    if (id) {
      setQuery(id);
      runSearch(id);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, runSearch, setSearchParams]);

  const reset = () => {
    setDetail(null);
    setResults(null);
    setMessage(null);
    setQuery("");
  };

  return (
    <div className="px-8 py-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">Search &amp; Details</h2>
        <p className="text-sm text-slate-500">
          Search by incident ID (e.g. INC-001) or by description/symptoms (e.g. database timeout, HTTP 500).
        </p>
      </div>

      <div className="card mb-6 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[260px] flex-1">
            <label className="label">Incident ID or Description</label>
            <input
              className="input"
              placeholder="e.g. INC-001  OR  connection pool exhausted, HTTP 500"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch(query, appFilter)}
            />
          </div>
          <div className="w-56">
            <label className="label">Application (optional)</label>
            <input
              className="input"
              placeholder="e.g. Payment Gateway"
              value={appFilter}
              onChange={(e) => setAppFilter(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch(query, appFilter)}
            />
          </div>
          <button className="btn-primary" onClick={() => runSearch(query, appFilter)} disabled={loading}>
            {loading ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
            Search
          </button>
          {(detail || results) && (
            <button className="btn-secondary" onClick={reset}>
              <RotateCcw className="h-4 w-4" /> New Search
            </button>
          )}
        </div>
      </div>

      {message && (
        <div className="card mb-6 flex items-center gap-2 border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {message}
        </div>
      )}

      {detail && <IncidentDetail data={detail} />}

      {results && (
        <div className="space-y-4">
          <p className="text-sm font-medium text-slate-500">
            Found {results.total} matching incident{results.total === 1 ? "" : "s"}
          </p>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {results.results.map((r) => (
              <ResultCard key={r.incident.incident_id} result={r} onOpen={setDetail} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
