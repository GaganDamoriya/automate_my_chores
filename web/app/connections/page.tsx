"use client";
import { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getConnections, disconnectProvider, loginUrl, type Connection } from "@/lib/api";

const ICON: Record<string, string> = { google: "🟥", slack: "🟪", github: "⬛", jira: "🟦" };

const ERROR_MSG: Record<string, string> = {
  not_configured: "That provider's OAuth app isn't configured yet — add its client ID & secret to .env.",
  bad_state: "The sign-in link expired or didn't match. Try Connect again.",
  exchange_failed: "Couldn't complete the token exchange. Check the app's redirect URI and secret.",
  access_denied: "You declined the authorization.",
};

function Banner() {
  const sp = useSearchParams();
  const connected = sp.get("connected");
  const error = sp.get("error");
  const provider = sp.get("provider");
  if (connected)
    return <div className="mb-6 bg-good/10 border border-good/40 rounded-xl px-4 py-3 text-sm text-good">
      ✓ Connected <b className="capitalize">{connected}</b>. Automations will now use it.
    </div>;
  if (error)
    return <div className="mb-6 bg-hot/10 border border-hot/40 rounded-xl px-4 py-3 text-sm text-hot">
      {ERROR_MSG[error] ?? `Connection failed (${error})`}{provider ? ` · ${provider}` : ""}
    </div>;
  return null;
}

function ConnectionsInner() {
  const [conns, setConns] = useState<Connection[] | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try { setConns(await getConnections()); setError(false); } catch { setError(true); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  async function disconnect(p: string) {
    setBusy(p);
    try { await disconnectProvider(p); await refresh(); } catch {} finally { setBusy(null); }
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-12">
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-xs text-accent uppercase tracking-widest">Invisible Work Detector</div>
            <h1 className="text-3xl font-bold mt-1">Connections</h1>
          </div>
          <Link href="/" className="font-mono text-xs font-semibold px-4 py-2 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent">
            ← Dashboard
          </Link>
        </div>
        <p className="text-slate-400 mt-2 font-mono text-sm">
          Authorize a tool once — automations act through it. Not connected? They fall back to safe simulation.
        </p>
      </header>

      <Banner />

      {error && (
        <div className="bg-surface2 border border-line rounded-xl p-5 text-slate-300">
          Backend not reachable. Start it with <span className="font-mono text-accent">make api</span>, then reload.
        </div>
      )}

      {conns && (
        <div className="space-y-3">
          {conns.map((c) => (
            <div key={c.provider} className="flex items-center gap-4 bg-surface border border-line rounded-xl px-4 py-4">
              <span className="text-2xl">{ICON[c.provider] ?? "🔌"}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{c.label}</span>
                  {c.connected ? (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-good/50 text-good">connected</span>
                  ) : c.configured ? (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-600 text-slate-400">not connected</span>
                  ) : (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-hot/50 text-hot">needs setup</span>
                  )}
                </div>
                <div className="font-mono text-[11px] text-slate-500 mt-0.5 truncate">
                  {c.connected && c.account ? c.account + " · " : ""}{c.scope}
                </div>
              </div>
              {c.connected ? (
                <button
                  onClick={() => disconnect(c.provider)}
                  disabled={busy === c.provider}
                  className="font-mono text-xs font-semibold px-3 py-2 rounded-lg border border-hot text-hot hover:bg-hot/10 disabled:opacity-50"
                >
                  {busy === c.provider ? "…" : "Disconnect"}
                </button>
              ) : c.configured ? (
                <a
                  href={loginUrl(c.provider)}
                  className="font-mono text-xs font-semibold px-3 py-2 rounded-lg border border-accent text-accent hover:bg-accent/10"
                >
                  Connect →
                </a>
              ) : (
                <span className="font-mono text-[11px] text-slate-600 max-w-[9rem] text-right">
                  add client id/secret to .env
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {!conns && !error && <p className="text-slate-500 text-sm">Loading…</p>}
    </main>
  );
}

export default function ConnectionsPage() {
  // useSearchParams needs a Suspense boundary in the app router.
  return (
    <Suspense fallback={<p className="text-slate-500 text-sm p-12">Loading…</p>}>
      <ConnectionsInner />
    </Suspense>
  );
}
