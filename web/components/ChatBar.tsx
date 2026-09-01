"use client";
import { useState } from "react";
import Link from "next/link";
import { chat, type ChatResponse } from "@/lib/api";

const EXAMPLES = [
  "Every morning post a Jira digest to #standup",
  "Clean up the customer CSV daily and email me",
  "Watch for tickets that keep getting reopened",
];

export function ChatBar() {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [resp, setResp] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(text?: string) {
    const message = (text ?? value).trim();
    if (!message || busy) return;
    setBusy(true); setError(null); setResp(null);
    try {
      const r = await chat(message);
      setResp(r);
      if (r.intent === "build") setValue("");
    } catch {
      setError("Backend not reachable — start it with `make seed && make api`.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-surface border border-line rounded-2xl p-4 shadow-lg">
      <form
        onSubmit={(e) => { e.preventDefault(); submit(); }}
        className="flex items-center gap-2"
      >
        <span className="text-accent text-lg pl-1">⌘</span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Describe an automation, or ask what to automate…"
          className="flex-1 bg-transparent outline-none text-[15px] placeholder:text-slate-500 py-2"
          autoFocus
        />
        <button
          type="submit"
          disabled={busy}
          className="font-mono text-xs font-semibold px-4 py-2 rounded-lg bg-accent text-ink disabled:opacity-50"
        >
          {busy ? "…" : "Run"}
        </button>
      </form>

      <div className="flex flex-wrap gap-2 mt-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => { setValue(ex); submit(ex); }}
            className="font-mono text-[11px] text-slate-400 border border-line rounded-full px-3 py-1 hover:border-accent hover:text-accent"
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <p className="mt-3 text-sm text-hot">{error}</p>}

      {resp && (
        <div className="mt-4 border-t border-line pt-4">
          <p className="text-sm text-slate-200 whitespace-pre-wrap">{renderReply(resp.reply)}</p>
          {resp.created_automation && (
            <div className="mt-3 flex items-center gap-3 bg-good/10 border border-good/40 rounded-lg px-3 py-2">
              <span className="text-good">✓</span>
              <span className="text-sm">
                <b>{resp.created_automation.name}</b> is now running.
              </span>
              <Link href="/automations" className="ml-auto font-mono text-xs text-accent hover:underline">
                Open Automations →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Render **bold** markers coming back from the API as real emphasis.
function renderReply(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : <span key={i}>{p}</span>
  );
}
