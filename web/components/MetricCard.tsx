export function MetricCard({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <div className={`text-3xl font-bold tabular-nums ${accent ? "text-accent" : ""}`}>{value}</div>
      <div className="mt-2 text-[11px] uppercase tracking-wider text-slate-400 font-mono">{label}</div>
    </div>
  );
}
