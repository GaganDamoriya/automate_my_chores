"use client";
import { useEffect, useRef, useState } from "react";
import {
  API_BASE, pauseAutomation, resumeAutomation, runAutomation, deleteAutomation, listRuns,
  type Automation, type Run,
} from "@/lib/api";
import { RunHistory } from "./RunHistory";

const KIND_BADGE: Record<string, { label: string; cls: string }> = {
  workflow: { label: "workflow", cls: "border-accent/50 text-accent" },
  rework: { label: "rework", cls: "border-hot/50 text-hot" },
  custom: { label: "custom", cls: "border-good/50 text-good" },
};

type Line = { i: number; agent: string; text: string };

function fmtWhen(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = (d.getTime() - Date.now()) / 1000;
  const a = Math.abs(diff);
  const unit = a < 60 ? [a, "s"] : a < 3600 ? [a / 60, "m"] : a < 86400 ? [a / 3600, "h"] : [a / 86400, "d"];
  const n = Math.round(unit[0] as number);
  return diff >= 0 ? `in ${n}${unit[1]}` : `${n}${unit[1]} ago`;
}

export function AutomationCard({ auto, onChange }: { auto: Automation; onChange: () => void }) {
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // live tailing of the current run over SSE
  const [live, setLive] = useState<Line[]>([]);
  const [liveStatus, setLiveStatus] = useState<string>("idle");
  const esRef = useRef<EventSource | null>(null);
  const curRunRef = useRef<string | null>(null);
  const doneRef = useRef<string | null>(null);

  const active = auto.status === "active";
  const badge = KIND_BADGE[auto.kind] ?? KIND_BADGE.workflow;
  const cadence = auto.interval_seconds ? `every ${auto.interval_seconds}s` : auto.cadence;
  const running = liveStatus === "running";

  async function refreshRuns() {
    try { setRuns(await listRuns(auto.id)); } catch {}
  }

  // Open/close the SSE stream with the expander.
  useEffect(() => {
    if (!open) {
      esRef.current?.close();
      esRef.current = null;
      return;
    }
    if (runs === null) refreshRuns();
    const es = new EventSource(`${API_BASE}/automations/${auto.id}/stream`);
    esRef.current = es;
    es.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m._run_start) {
        curRunRef.current = m._run_start;
        setLive([]);            // a new run is about to stream — reset the feed
        setLiveStatus("running");
        return;
      }
      if (typeof m.i === "number") {
        setLive((p) => (p.some((l) => l.i === m.i) ? p : [...p, m]));
        return;
      }
      if (m._status) {
        const rid = m.run_id ?? null;
        if (rid && rid !== curRunRef.current) {
          curRunRef.current = rid;
          if (m._status === "running") setLive([]); // a new run started — reset the feed
        }
        setLiveStatus(m._status);
        if ((m._status === "done" || m._status === "failed") && rid && doneRef.current !== rid) {
          doneRef.current = rid;
          refreshRuns();
          onChange();
        }
      }
    };
    es.onerror = () => { /* browser auto-reconnects; server ends the stream when a run finishes */ };
    return () => { es.close(); esRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, auto.id]);

  async function toggleOpen() {
    setOpen((o) => !o);
  }

  async function act(kind: "toggle" | "run" | "delete") {
    setBusy(kind);
    try {
      if (kind === "toggle") active ? await pauseAutomation(auto.id) : await resumeAutomation(auto.id);
      else if (kind === "run") { setOpen(true); await runAutomation(auto.id); await refreshRuns(); }
      else if (kind === "delete") { await deleteAutomation(auto.id); }
      onChange();
    } catch {} finally { setBusy(null); }
  }

  return (
    <div className="bg-surface border border-line rounded-xl overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <span
          className={`h-2.5 w-2.5 rounded-full shrink-0 ${
            running ? "bg-accent animate-pulse" : active ? "bg-good animate-pulse" : "bg-slate-600"
          }`}
          title={running ? "running" : active ? "active" : "paused"}
        />
        <button onClick={toggleOpen} className="flex-1 min-w-0 text-left">
          <div className="flex items-center gap-2">
            <span className="font-semibold truncate">{auto.name}</span>
            <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${badge.cls}`}>
              {badge.label}
            </span>
            {running && (
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-accent/50 text-accent animate-pulse">
                running…
              </span>
            )}
          </div>
          <div className="font-mono text-[11px] text-slate-400 mt-0.5">
            {cadence} · {active ? `next ${fmtWhen(auto.next_run_at)}` : "paused"} ·{" "}
            {auto.run_count ?? 0} run{(auto.run_count ?? 0) === 1 ? "" : "s"}
            {auto.last_run_at ? ` · last ${fmtWhen(auto.last_run_at)}` : ""}
          </div>
        </button>

        <button
          onClick={() => act("run")}
          disabled={!!busy}
          className="font-mono text-xs font-semibold px-3 py-1.5 rounded-lg border border-line text-slate-300 hover:border-accent hover:text-accent disabled:opacity-50"
        >
          {busy === "run" ? "…" : "Run now"}
        </button>
        <button
          onClick={() => act("toggle")}
          disabled={!!busy}
          className={`font-mono text-xs font-semibold px-3 py-1.5 rounded-lg border disabled:opacity-50 ${
            active ? "border-hot text-hot hover:bg-hot/10" : "border-good text-good hover:bg-good/10"
          }`}
        >
          {busy === "toggle" ? "…" : active ? "Stop" : "Restart"}
        </button>
        <button onClick={toggleOpen} className="text-slate-500 hover:text-slate-300 px-1" title="History">
          {open ? "▾" : "▸"}
        </button>
      </div>

      {open && (
        <div className="border-t border-line px-4 pb-4 bg-ink/30">
          <p className="text-sm text-slate-400 py-3">{auto.description}</p>

          {/* live run feed (only while a run is actively streaming) */}
          {running && live.length > 0 && (
            <div className="mb-3 border border-accent/40 rounded-xl p-3 bg-ink/40">
              <div className="font-mono text-[11px] uppercase tracking-wider text-accent mb-2 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" /> live run
              </div>
              <div className="space-y-1 font-mono text-xs">
                {live.map((l) => (
                  <div key={l.i} className="flex gap-2">
                    <span className="text-accent shrink-0">{l.agent}</span>
                    <span className="text-slate-300">{l.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <RunHistory runs={runs ?? []} kind={auto.kind} />
          <div className="pt-3">
            <button
              onClick={() => act("delete")}
              disabled={!!busy}
              className="font-mono text-[11px] text-slate-600 hover:text-hot disabled:opacity-50"
            >
              {busy === "delete" ? "deleting…" : "Delete automation"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
