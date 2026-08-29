// Thin client for the Invisible Work Detector API.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Opportunity = {
  id: string;
  name: string;
  actor: string;
  tools: string[];
  cadence: string;
  minutes_per_run: number;
  occurrences: number;
  annual_hours_est: number;
  score: number;
  risk: string;
  recommended_action: string;
};

export type DiscoveryResult = {
  metrics: {
    workflows_discovered: number;
    automation_opportunities: number;
    potential_hours_per_month: number;
    rework_hours_this_period: number;
  };
  opportunities: Opportunity[];
};

export async function getDiscovery(): Promise<DiscoveryResult> {
  const res = await fetch(`${API_BASE}/discovery/run`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export type Run = {
  id: string;
  status: string;
  opportunity_name?: string | null;
  approved: boolean;
  log: { i: number; agent: string; text: string; ts: string }[];
  result?: { verified: boolean; human_steps_eliminated: number; time_saved_min: number } | null;
};

export async function startRun(): Promise<Run> {
  const r = await fetch(`${API_BASE}/runs`, { method: "POST" });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function approveRun(id: string): Promise<Run> {
  const r = await fetch(`${API_BASE}/runs/${id}/approve`, { method: "POST" });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export type ReworkTheme = {
  theme: string;
  count: number;
  stages: string[];
  example_quote: string;
  tickets: string[];
};

export type ReworkReport = {
  week_of: string;
  metrics: { tickets_reopened: number; total_reopens: number; avg_reopens_per_ticket: number };
  repeating_issues: ReworkTheme[];
  most_reopened_tickets: { ticket: string; title: string; reopens: number; stages: string[] }[];
  what_to_look_into: string | null;
};

export async function getReworkReport(): Promise<ReworkReport> {
  const res = await fetch(`${API_BASE}/rework/report`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
