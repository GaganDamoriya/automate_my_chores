"use client";
import { useState } from "react";
import Link from "next/link";
import { createAutomation, type Opportunity } from "@/lib/api";

function cadenceKey(c: string) {
  const t = c.toLowerCase();
  if (t.includes("week")) return "weekly";
  if (t.includes("day") || t.includes("daily")) return "daily";
  return "daily";
}

export function SuggestionCard({ opp }: { opp: Opportunity }) {
  const [state, setState] = useState<"idle" | "creating" | "done">("idle");
  const hot = opp.annual_hours_est >= 40;

  async function automate() {
    if (state !== "idle") return;
    setState("creating");
    try {
      await createAutomation({
        name: opp.name,
        description: `Discovered workflow: ${opp.tools.join(" → ")}`,
        kind: "workflow",
        spec: { workflow_name: opp.name, tools: opp.tools },
        cadence: cadenceKey(opp.cadence),
        confirm_channel: "slack",
        confirm_target: "#automations",
        status: "active",
      });
      setState("done");
    } catch {
      setState("idle");
    }
  }

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
      {state === "done" ? (
        <Link
          href="/automations"
          className="font-mono text-xs font-semibold px-3 py-2 rounded-lg border border-good text-good"
        >
          ✓ Automated →
        </Link>
      ) : (
        <button
          onClick={automate}
          disabled={state === "creating"}
          className="font-mono text-xs font-semibold px-3 py-2 rounded-lg border border-accent text-accent hover:bg-accent/10 disabled:opacity-50"
        >
          {state === "creating" ? "…" : "Automate"}
        </button>
      )}
    </div>
  );
}
