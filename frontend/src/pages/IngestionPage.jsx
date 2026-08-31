import { useEffect, useState } from "react";
import { DownloadCloud, Database, CheckCircle2, AlertTriangle, Rocket } from "lucide-react";
import { api } from "../api/client.js";
import { Spinner } from "../components/ui.jsx";

function StatTile({ label, value, accent }) {
  const accents = {
    slate: "text-slate-900",
    brand: "text-brand-600",
    emerald: "text-emerald-600",
    red: "text-red-600",
  };
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 text-center">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accents[accent] || accents.slate}`}>{value}</p>
    </div>
  );
}

export default function IngestionPage() {
  const [total, setTotal] = useState(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const loadStatus = async () => {
    try {
      const data = await api.dashboard();
      setTotal(data.total_incidents);
    } catch {
      setTotal(null);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const runIngestion = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runIngestion();
      setResult(res);
      await loadStatus();
    } catch (err) {
      setError(err.message || "Ingestion failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="px-8 py-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">Data Ingestion</h2>
        <p className="text-sm text-slate-500">
          Load mock Google Chat conversations and extract structured incidents into the knowledge base.
        </p>
      </div>

      <div className="mx-auto max-w-3xl space-y-6">
        <div className="card flex items-center gap-4 p-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Current knowledge base</p>
            <p className="text-2xl font-bold text-slate-900">
              {total === null ? "—" : `${total} incidents`}
            </p>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-800">
            <DownloadCloud className="h-5 w-5 text-brand-600" /> Ingest Mock Google Chat Data
          </h3>
          <ol className="mb-4 space-y-2 text-sm text-slate-600">
            {[
              "Load conversations from data/original_incident_data.json",
              "Group messages by thread",
              "Extract structured incidents using AI",
              "Store incidents in the knowledge base",
              "Index incidents for semantic search",
            ].map((step, i) => (
              <li key={i} className="flex gap-2">
                <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>

          <div className="mb-5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>
              Running ingestion <strong>clears all existing incidents and the search index first</strong>, then
              reloads everything fresh.
            </span>
          </div>

          <button className="btn-primary w-full sm:w-auto" onClick={runIngestion} disabled={running}>
            {running ? <Spinner className="h-4 w-4" /> : <Rocket className="h-4 w-4" />}
            {running ? "Ingesting…" : "Run Ingestion"}
          </button>

          {running && (
            <p className="mt-3 text-sm text-slate-500">
              This may take a moment while each conversation is processed in parallel.
            </p>
          )}
        </div>

        {error && (
          <div className="card flex items-center gap-2 border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {result && (
          <div className="card animate-fade-in p-6">
            <div className="mb-4 flex items-center gap-2 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
              <h3 className="font-semibold">Ingestion completed successfully</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Threads" value={result.total_threads} accent="slate" />
              <StatTile label="Extracted" value={result.incidents_extracted} accent="brand" />
              <StatTile label="Successful" value={result.successful} accent="emerald" />
              <StatTile label="Failed" value={result.failed} accent="red" />
            </div>
            {result.failed > 0 && (
              <p className="mt-4 flex items-center gap-2 text-sm text-amber-700">
                <AlertTriangle className="h-4 w-4" />
                {result.failed} thread(s) failed to process. Check backend logs for details.
              </p>
            )}
            <p className="mt-4 text-sm text-slate-600">
              You can now explore the data in <strong>Historical Incidents</strong> or{" "}
              <strong>Search &amp; Details</strong>, or ask questions in <strong>Incident Chat</strong>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
