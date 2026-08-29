import Link from "next/link";
import { getDiscovery } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { OpportunityRow } from "@/components/OpportunityRow";
import { RunPanel } from "@/components/RunPanel";

export default async function Dashboard() {
  let data = null;
  try {
    data = await getDiscovery();
  } catch {
    /* API not running — show the shell with a hint */
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <header className="mb-8">
        <div className="font-mono text-xs text-accent uppercase tracking-widest">Invisible Work Detector</div>
        <h1 className="text-3xl font-bold mt-1">Dashboard</h1>
        <p className="text-slate-400 mt-1 font-mono text-sm">We don&apos;t watch people. We watch workflows.</p>
        <nav className="mt-3 flex gap-4 font-mono text-xs">
          <span className="text-accent">Dashboard</span>
          <Link href="/rework" className="text-slate-400 hover:text-accent">Rework Report →</Link>
        </nav>
      </header>

      {!data && (
        <div className="bg-surface2 border border-line rounded-xl p-5 mb-8 text-slate-300">
          Backend not reachable. Start it with <span className="font-mono text-accent">make seed &amp;&amp; make api</span>,
          then reload.
        </div>
      )}

      {data && (
        <>
          <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            <MetricCard value={String(data.metrics.workflows_discovered)} label="Workflows discovered" />
            <MetricCard value={String(data.metrics.automation_opportunities)} label="Opportunities" />
            <MetricCard value={`${data.metrics.potential_hours_per_month}h`} label="Potential / month" accent />
            <MetricCard value={`${data.metrics.rework_hours_this_period}h`} label="Rework this period" accent />
          </section>

          <section className="mb-8">
            <h2 className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-3">Top opportunities</h2>
            <div className="space-y-2">
              {data.opportunities.map((o) => <OpportunityRow key={o.id} opp={o} />)}
            </div>
          </section>
        </>
      )}

      <section>
        <RunPanel />
      </section>
    </main>
  );
}
