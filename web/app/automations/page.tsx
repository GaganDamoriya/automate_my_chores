"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listAutomations, createFromDescription, type Automation } from "@/lib/api";
import { AutomationCard } from "@/components/AutomationCard";

export default function AutomationsPage() {
  const [autos, setAutos] = useState<Automation[] | null>(null);
  const [error, setError] = useState(false);
  const [desc, setDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setAutos(await listAutomations());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000); // live status + scheduler-produced runs
    return () => clearInterval(t);
  }, [refresh]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    const d = desc.trim();
    if (!d || creating) return;
    setCreating(true);
    try {
      await createFromDescription(d);
      setDesc("");
      await refresh();
    } catch {} finally {
      setCreating(false);
    }
  }

  const active = autos?.filter((a) => a.status === "active").length ?? 0;
  const total = autos?.length ?? 0;

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-xs text-accent uppercase tracking-widest">
              Invisible Work Detector
            </div>
            <h1 className="text-3xl font-bold mt-1">Automations</h1>
          </div>
          <nav className="flex gap-2">
            <Link
              href="/connections"
              className="font-mono text-xs font-semibold px-4 py-2 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent"
            >
              Connections
            </Link>
            <Link
              href="/"
              className="font-mono text-xs font-semibold px-4 py-2 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent"
            >
              ← Dashboard
            </Link>
          </nav>
        </div>
        <p className="text-slate-400 mt-2 font-mono text-sm">
          {total} automation{total === 1 ? "" : "s"} · {active} running · stop or restart any of them anytime.
        </p>
      </header>

      {/* quick create */}
      <form onSubmit={create} className="flex items-center gap-2 bg-surface border border-line rounded-xl p-3 mb-8">
        <span className="text-accent pl-1">＋</span>
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Describe a new automation…  e.g. every hour check GitHub and post to #dev"
          className="flex-1 bg-transparent outline-none text-sm placeholder:text-slate-500 py-1"
        />
        <button
          type="submit"
          disabled={creating}
          className="font-mono text-xs font-semibold px-4 py-2 rounded-lg bg-accent text-ink disabled:opacity-50"
        >
          {creating ? "…" : "Create"}
        </button>
      </form>

      {error && (
        <div className="bg-surface2 border border-line rounded-xl p-5 text-slate-300 mb-6">
          Backend not reachable. Start it with{" "}
          <span className="font-mono text-accent">make seed &amp;&amp; make api</span>, then reload.
        </div>
      )}

      {autos && autos.length > 0 && (
        <div className="space-y-3">
          {autos.map((a) => (
            <AutomationCard key={a.id} auto={a} onChange={refresh} />
          ))}
        </div>
      )}

      {autos && autos.length === 0 && !error && (
        <p className="text-slate-500 text-sm">
          No automations yet. Describe one above, or head to the{" "}
          <Link href="/" className="text-accent hover:underline">dashboard</Link> and Automate a suggestion.
        </p>
      )}

      {!autos && !error && <p className="text-slate-500 text-sm">Loading…</p>}
    </main>
  );
}
