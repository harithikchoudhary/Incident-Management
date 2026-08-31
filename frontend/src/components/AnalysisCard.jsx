// Renders the structured resolution analysis returned by the /chat and
// /analyze endpoints (confidence, root cause, resolution steps, matches).
import { CheckCircle2, AlertTriangle, XCircle, Target, ListChecks, FileSearch } from "lucide-react";

const CONFIDENCE_ICON = {
  HIGH: { icon: CheckCircle2, color: "text-emerald-600" },
  MEDIUM: { icon: AlertTriangle, color: "text-amber-600" },
  LOW: { icon: XCircle, color: "text-red-600" },
};

export default function AnalysisCard({ analysis }) {
  if (!analysis) return null;

  const confidence = analysis.confidence ?? 0;
  const level = analysis.confidence_level || "LOW";
  const ConfMeta = CONFIDENCE_ICON[level] || CONFIDENCE_ICON.LOW;
  const ConfIcon = ConfMeta.icon;

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <Target className="h-4 w-4 text-brand-600" />
        <h4 className="text-sm font-semibold text-slate-700">Detailed Analysis</h4>
      </div>

      <div className="space-y-4 p-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
            <p className="text-xs font-medium text-slate-500">Similarity</p>
            <p className="text-lg font-bold text-slate-900">{Math.round(confidence * 100)}%</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
            <p className="text-xs font-medium text-slate-500">Confidence</p>
            <p className={`flex items-center justify-center gap-1 text-lg font-bold ${ConfMeta.color}`}>
              <ConfIcon className="h-4 w-4" />
              {level}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
            <p className="text-xs font-medium text-slate-500">Matches</p>
            <p className="text-lg font-bold text-slate-900">
              {(analysis.matched_incidents || []).length}
            </p>
          </div>
        </div>

        {analysis.likely_root_cause && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <FileSearch className="h-3.5 w-3.5" /> Root Cause
            </p>
            <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-slate-700">
              {analysis.likely_root_cause}
            </p>
          </div>
        )}

        {analysis.recommended_resolution?.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <ListChecks className="h-3.5 w-3.5" /> Resolution Steps
            </p>
            <ol className="space-y-1.5">
              {analysis.recommended_resolution.map((step, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-700">
                  <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {analysis.matched_incidents?.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Matched Historical Incidents
            </p>
            <div className="space-y-1.5">
              {analysis.matched_incidents.map((m) => (
                <div
                  key={m.incident_id}
                  className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                >
                  <span className="font-mono font-semibold text-brand-700">{m.incident_id}</span>
                  <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
                    {Math.round((m.similarity ?? 0) * 100)}%
                  </span>
                  <span className="text-slate-600">{m.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {analysis.warnings?.length > 0 && (
          <div className="space-y-1.5">
            {analysis.warnings.map((w, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
