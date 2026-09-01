"use client";
import type { Run } from "@/lib/api";

const THEME_LABELS: Record<string, string> = {
  missing_tests: "Missing edge-case tests",
  null_handling: "Null / missing-data handling",
  spec_misunderstanding: "Spec misunderstanding",
  error_handling: "Error handling",
  flaky_test: "Flaky tests",
  style: "Style / readability",
  other: "Other",
};

function ReworkView({ data }: { data: any }) {
  const issues: any[] = data?.repeating_issues ?? [];
  const max = Math.max(1, ...issues.map((i) => i.count));
  return (
    <div className="mt-2 space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <Stat n={data.metrics?.tickets_reopened} l="Tickets reopened" />
        <Stat n={data.metrics?.total_reopens} l="Total reopens" accent />
        <Stat n={data.metrics?.avg_reopens_per_ticket} l="Avg / ticket" />
      </div>
      {issues.map((it) => (
        <div key={it.theme} className="bg-ink/40 border border-line rounded-lg p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold">🔁 {THEME_LABELS[it.theme] ?? it.theme}</span>
            <span className="font-mono text-accent tabular-nums">{it.count}</span>
          </div>
          <div className="mt-1.5 h-1.5 rounded bg-surface2 overflow-hidden">
            <div className="h-full bg-accent" style={{ width: `${(it.count / max) * 100}%` }} />
          </div>
          <p className="mt-2 text-xs text-slate-400 italic">“{it.example_quote}”</p>
        </div>
      ))}
      {data.what_to_look_into && (
        <div className="bg-hot/10 border-l-2 border-hot rounded px-3 py-2 text-sm text-slate-200">
          {data.what_to_look_into}
        </div>
      )}
    </div>
  );
}

function Stat({ n, l, accent }: { n: any; l: string; accent?: boolean }) {
  return (
    <div className="bg-ink/40 border border-line rounded-lg p-2 text-center">
      <div className={`text-lg font-bold tabular-nums ${accent ? "text-accent" : ""}`}>{n ?? "–"}</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">{l}</div>
    </div>
  );
}

function Confirmation({ c }: { c: NonNullable<Run["confirmation"]> }) {
  return (
    <div className="mt-2 bg-ink/40 border border-line rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
          Confirmation · {c.channel}
          {c.target ? ` → ${c.target}` : ""}
        </span>
        <span
          className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
            c.sent ? "border-good/50 text-good" : "border-hot/50 text-hot"
          }`}
        >
          {c.sent ? "sent ✓" : "simulated"}
        </span>
      </div>
      <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">{c.body}</pre>
      {!c.sent && c.detail && <p className="mt-1 text-[11px] text-slate-500">{c.detail}</p>}
    </div>
  );
}

export function RunHistory({ runs, kind }: { runs: Run[]; kind: string }) {
  if (!runs || runs.length === 0)
    return <p className="text-sm text-slate-500 py-3">No runs yet. Hit “Run now” to fire one.</p>;

  return (
    <div className="space-y-3 pt-2">
      {runs.map((r) => (
        <div key={r.id} className="border border-line rounded-xl p-3 bg-surface2">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span
              className={`px-1.5 py-0.5 rounded border ${
                r.status === "done"
                  ? "border-good/50 text-good"
                  : r.status === "failed"
                  ? "border-hot/50 text-hot"
                  : "border-accent/50 text-accent"
              }`}
            >
              {r.status}
            </span>
            <span>· {r.trigger}</span>
            <span className="ml-auto">{r.created_at?.replace("T", " ").replace("Z", "")}</span>
          </div>

          {/* recorded data */}
          {kind === "rework" && r.data_produced ? (
            <ReworkView data={r.data_produced} />
          ) : (
            r.data_produced && (
              <div className="mt-2 text-sm">
                <div className="text-slate-200">{(r.data_produced as any).produced_summary}</div>
                {(r.data_produced as any).steps_performed && (
                  <div className="font-mono text-[11px] text-slate-500 mt-1">
                    {(r.data_produced as any).steps_performed.join(" → ")}
                  </div>
                )}
                {typeof (r.data_produced as any).time_saved_min === "number" && (
                  <div className="font-mono text-[11px] text-good mt-1">
                    ✓ {(r.data_produced as any).human_steps_eliminated} steps eliminated · ~
                    {(r.data_produced as any).time_saved_min} min saved
                  </div>
                )}
              </div>
            )
          )}

          {/* confirmation sent */}
          {r.confirmation && <Confirmation c={r.confirmation} />}
        </div>
      ))}
    </div>
  );
}
