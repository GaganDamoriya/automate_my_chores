"use client";
import { useEffect, useRef, useState } from "react";
import { API_BASE, startRun, approveRun } from "@/lib/api";

type Line = { i: number; agent: string; text: string };

export function RunPanel() {
  const [runId, setRunId] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [status, setStatus] = useState<string>("idle");
  const [opp, setOpp] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  function connect(id: string) {
    esRef.current?.close();
    const es = new EventSource(`${API_BASE}/runs/${id}/stream`);
    esRef.current = es;
    es.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (typeof m.i === "number") setLines((p) => (p.some((l) => l.i === m.i) ? p : [...p, m]));
      else if (m._status) {
        setStatus(m._status);
        setOpp(m.opportunity ?? null);
        if (m._status === "done" || m._status === "failed") es.close();
      }
    };
    es.onerror = () => es.close();
  }

  // Reconnect to an in-flight run after a reload — proves durability.
  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("iwd_run") : null;
    if (saved) { setRunId(saved); setLines([]); connect(saved); }
    return () => esRef.current?.close();
  }, []);

  async function onStart() {
    setLines([]); setOpp(null); setStatus("starting");
    const run = await startRun();
    setRunId(run.id);
    try { localStorage.setItem("iwd_run", run.id); } catch {}
    connect(run.id);
  }

  async function onApprove() {
    if (!runId) return;
    await approveRun(runId);
    connect(runId); // resume tailing execute → verify
  }

  const gate = status === "awaiting_approval";
  const done = status === "done";

  return (
    <div className="bg-surface border border-line rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-line">
        <span className="font-mono text-xs text-slate-400 uppercase tracking-wider">
          Autonomous run {runId ? `· ${runId}` : ""}
        </span>
        <div className="flex gap-2">
          <button onClick={onStart}
            className="font-mono text-xs font-semibold px-3 py-1.5 rounded-lg border border-accent text-accent">
            Detect &amp; run
          </button>
          {gate && (
            <button onClick={onApprove}
              className="font-mono text-xs font-semibold px-3 py-1.5 rounded-lg border border-hot text-hot animate-pulse">
              Approve &amp; execute
            </button>
          )}
        </div>
      </div>

      {gate && (
        <div className="px-4 py-2 bg-hot/10 border-b border-line font-mono text-xs text-hot">
          Paused for approval{opp ? ` · ${opp}` : ""} — try closing this tab and reopening it; the run keeps going.
        </div>
      )}
      {done && (
        <div className="px-4 py-2 bg-good/10 border-b border-line font-mono text-xs text-good">
          Verified ✓ — work eliminated. Reload the page any time; the run state is durable.
        </div>
      )}

      <div className="p-4 space-y-2 min-h-[200px] font-mono text-sm">
        {lines.length === 0 && <div className="text-slate-500">Press “Detect &amp; run” to start an autonomous run.</div>}
        {lines.map((l) => (
          <div key={l.i} className="flex gap-3">
            <span className={`shrink-0 ${l.agent === "human" ? "text-hot" : "text-accent"}`}>{l.agent}</span>
            <span className="text-slate-300">{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
