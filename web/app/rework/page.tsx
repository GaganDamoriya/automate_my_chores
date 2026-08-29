import Link from "next/link";
import { getReworkReport } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";

const LABELS: Record<string, string> = {
  missing_tests: "Missing edge-case tests",
  null_handling: "Null / missing-data handling",
  spec_misunderstanding: "Spec misunderstanding",
  error_handling: "Error handling",
  flaky_test: "Flaky tests",
  style: "Style / readability",
  other: "Other",
};
const label = (t: string) => LABELS[t] ?? t;

function Stage({ s }: { s: string }) {
  const review = s === "review";
  return (
    <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
      review ? "border-accent/50 text-accent" : "border-hot/50 text-hot"}`}>
      {review ? "code review" : "QA"}
    </span>
  );
}

export default async function ReworkPage() {
  let data = null;
  try { data = await getReworkReport(); } catch { /* API down */ }
  const max = data ? Math.max(1, ...data.repeating_issues.map((i) => i.count)) : 1;

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <header className="mb-8">
        <div className="font-mono text-xs text-accent uppercase tracking-widest">Invisible Work Detector</div>
        <div className="flex items-baseline justify-between flex-wrap gap-2 mt-1">
          <h1 className="text-3xl font-bold">Weekly Rework Report</h1>
          {data && <span className="font-mono text-xs text-slate-400">week of {data.week_of}</span>}
        </div>
        <nav className="mt-3 flex gap-4 font-mono text-xs">
          <Link href="/" className="text-slate-400 hover:text-accent">← Dashboard</Link>
          <span className="text-accent">Rework Report</span>
        </nav>
        <p className="mt-4 text-slate-400 text-sm max-w-2xl">
          The second kind of invisible work: hours lost to tickets bouncing back from review or QA.
          <span className="text-slate-500"> Ranks issues, not people — analytics are anonymized.</span>
        </p>
      </header>

      {!data && (
        <div className="bg-surface2 border border-line rounded-xl p-5 text-slate-300">
          Backend not reachable. Start it with <span className="font-mono text-accent">make seed &amp;&amp; make api</span>, then reload.
        </div>
      )}

      {data && (
        <>
          <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            <MetricCard value={String(data.metrics.tickets_reopened)} label="Tickets reopened" />
            <MetricCard value={String(data.metrics.total_reopens)} label="Total reopens" accent />
            <MetricCard value={String(data.metrics.avg_reopens_per_ticket)} label="Avg reopens / ticket" />
            <MetricCard value={String(data.repeating_issues.length)} label="Recurring themes" />
          </section>

          <section className="mb-8">
            <h2 className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-3">Repeating issues found</h2>
            <div className="space-y-3">
              {data.repeating_issues.map((it) => (
                <div key={it.theme} className="bg-surface border border-line rounded-xl p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 font-semibold">
                      <span>🔁</span>{label(it.theme)}
                    </div>
                    <div className="flex items-center gap-2">
                      {it.stages.map((s) => <Stage key={s} s={s} />)}
                      <span className="font-mono text-sm text-accent tabular-nums">{it.count}</span>
                    </div>
                  </div>
                  <div className="mt-2 h-2 rounded bg-surface2 overflow-hidden">
                    <div className="h-full rounded bg-accent" style={{ width: `${(it.count / max) * 100}%` }} />
                  </div>
                  <p className="mt-3 text-sm text-slate-400 italic">“{it.example_quote}”</p>
                  <p className="mt-1 font-mono text-[11px] text-slate-500">{it.tickets.length} tickets affected</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-8">
            <h2 className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-3">Most-reopened tickets</h2>
            <div className="space-y-2">
              {data.most_reopened_tickets.map((t) => (
                <div key={t.ticket} className="flex items-center gap-3 bg-surface2 border border-line rounded-xl px-4 py-3">
                  <span className="font-mono text-xs text-slate-500 w-24 shrink-0">{t.ticket}</span>
                  <span className="flex-1 min-w-0 truncate">{t.title}</span>
                  <div className="flex gap-1">{t.stages.map((s, i) => <Stage key={i} s={s} />)}</div>
                  <span className="font-mono text-xs font-semibold text-hot tabular-nums">{t.reopens}×</span>
                </div>
              ))}
            </div>
          </section>

          {data.what_to_look_into && (
            <section className="bg-surface border-l-4 border-hot border-t border-r border-b border-line rounded-xl p-5">
              <div className="font-mono text-[11px] uppercase tracking-wider text-slate-400 mb-2">What to look into</div>
              <p className="text-slate-200">{data.what_to_look_into}</p>
            </section>
          )}
        </>
      )}
    </main>
  );
}
