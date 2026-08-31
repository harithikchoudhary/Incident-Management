// Metric tile used on the dashboard.
export default function MetricCard({ label, value, icon: Icon, accent = "brand" }) {
  const accents = {
    brand: "bg-brand-50 text-brand-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
  };
  return (
    <div className="card flex items-center gap-4 p-5">
      {Icon && (
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${accents[accent]}`}>
          <Icon className="h-6 w-6" />
        </div>
      )}
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  );
}
