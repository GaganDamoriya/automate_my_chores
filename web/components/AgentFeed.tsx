"use client";
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

type Line = { agent: string; text: string };

export function AgentFeed() {
  const [lines, setLines] = useState<Line[]>([]);
  const [running, setRunning] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  function start() {
    setLines([]);
    setRunning(true);
    const es = new EventSource(`${API_BASE}/activity/stream`);
    esRef.current = es;
    es.onmessage = (e) => {
      const line = JSON.parse(e.data) as Line;
      setLines((prev) => [...prev, line]);
      if (line.agent === "done") { es.close(); setRunning(false); }
    };
    es.onerror = () => { es.close(); setRunning(false); };
  }

  useEffect(() => () => esRef.current?.close(), []);

  return (
    <div className="bg-surface border border-line rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-line">
        <span className="font-mono text-xs text-slate-400 uppercase tracking-wider">Agent activity</span>
        <button
          onClick={start}
          disabled={running}
          className="font-mono text-xs font-semibold px-3 py-1.5 rounded-lg border border-accent text-accent disabled:opacity-40"
        >
          {running ? "Investigating…" : "Run discovery"}
        </button>
      </div>
      <div className="p-4 space-y-2 min-h-[180px] font-mono text-sm">
        {lines.length === 0 && <div className="text-slate-500">Press “Run discovery” to watch the agent work.</div>}
        {lines.map((l, i) => (
          <div key={i} className="flex gap-3">
            <span className="text-accent shrink-0">{l.agent}</span>
            <span className="text-slate-300">{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
