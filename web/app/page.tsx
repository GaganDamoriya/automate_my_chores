import Link from "next/link";
import { getDiscovery } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { SuggestionCard } from "@/components/SuggestionCard";
import { ChatBar } from "@/components/ChatBar";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  let data = null;
  try {
    data = await getDiscovery();
  } catch {
    /* API not running — show the shell with a hint */
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-xs text-accent uppercase tracking-widest">
              Invisible Work Detector
            </div>
            <h1 className="text-3xl font-bold mt-1">What should we automate?</h1>
          </div>
          <nav className="flex gap-2">
            <Link
              href="/connections"
              className="font-mono text-xs font-semibold px-4 py-2 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent"
            >
              Connections
            </Link>
            <Link
              href="/automations"
              className="font-mono text-xs font-semibold px-4 py-2 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent"
            >
              Automations →
            </Link>
          </nav>
        </div>
        <p className="text-slate-400 mt-2 font-mono text-sm">
          We don&apos;t watch people. We watch workflows.
        </p>
      </header>

      {/* Primary control: describe-to-automate, or ask. */}
      <section className="mb-10">
        <ChatBar />
      </section>

      {!data && (
        <div className="bg-surface2 border border-line rounded-xl p-5 text-slate-300">
          Backend not reachable. Start it with{" "}
          <span className="font-mono text-accent">make seed &amp;&amp; make api</span>, then reload.
        </div>
      )}

      {data && (
        <>
          <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
            <MetricCard value={String(data.metrics.workflows_discovered)} label="Workflows watched" />
            <MetricCard value={String(data.metrics.automation_opportunities)} label="Opportunities" />
            <MetricCard value={`${data.metrics.potential_hours_per_month}h`} label="Potential / month" accent />
            <MetricCard value={`${data.metrics.rework_hours_this_period}h`} label="Rework this period" accent />
          </section>

          <section>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-mono text-xs uppercase tracking-wider text-slate-400">
                Invisible work we found
              </h2>
              <span className="font-mono text-[11px] text-slate-500">tap Automate to spin one up</span>
            </div>
            <div className="space-y-2">
              {data.opportunities.map((o) => (
                <SuggestionCard key={o.id} opp={o} />
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
