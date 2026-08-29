import type { Opportunity } from "@/lib/api";

export function OpportunityRow({ opp }: { opp: Opportunity }) {
  const hot = opp.annual_hours_est >= 40;
  return (
    <div className="flex items-center gap-4 bg-surface2 border border-line rounded-xl px-4 py-3">
      <span className="text-lg">{hot ? "🔥" : "🟡"}</span>
      <div className="flex-1 min-w-0">
        <div className="font-semibold">{opp.name}</div>
        <div className="font-mono text-xs text-slate-400 mt-0.5">
          {opp.minutes_per_run} min × {opp.cadence} → ~{opp.annual_hours_est} hrs/yr · {opp.tools.join(" → ")}
        </div>
      </div>
      <span className="font-mono text-[11px] text-slate-500">score {opp.score}</span>
      <button className="font-mono text-xs font-semibold px-3 py-2 rounded-lg border border-accent text-accent hover:bg-accent/10">
        {opp.recommended_action === "ELIMINATE" ? "Investigate" : "Automate"}
      </button>
    </div>
  );
}
