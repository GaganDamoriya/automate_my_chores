// Client for the Invisible Work Automation Platform API.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------- discovery

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

export const getDiscovery = () => j<DiscoveryResult>("/discovery/suggestions");

// ---------------------------------------------------------------- automations

export type Confirmation = {
  channel: string;
  target?: string | null;
  subject: string;
  body: string;
  sent: boolean;
  simulated: boolean;
  detail: string;
};

export type Run = {
  id: string;
  automation_id: string;
  trigger: string;
  status: string;
  created_at: string;
  finished_at?: string | null;
  log: { i: number; agent: string; text: string; ts: string }[];
  result?: Record<string, unknown> | null;
  data_produced?: Record<string, unknown> | null;
  confirmation?: Confirmation | null;
};

export type Automation = {
  id: string;
  name: string;
  description: string;
  kind: string; // workflow | rework | custom
  spec: Record<string, unknown>;
  cadence: string;
  interval_seconds?: number | null;
  status: string; // active | paused
  confirm_channel: string;
  confirm_target?: string | null;
  created_at: string;
  next_run_at?: string | null;
  last_run_at?: string | null;
  run_count?: number;
  last_run?: Run | null;
  runs?: Run[];
};

export const listAutomations = () =>
  j<{ automations: Automation[] }>("/automations").then((r) => r.automations);

export const getAutomation = (id: string) => j<Automation>(`/automations/${id}`);

export const createAutomation = (body: Partial<Automation>) =>
  j<Automation>("/automations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const createFromDescription = (description: string) =>
  j<{ automation: Automation; parsed: Record<string, unknown> }>(
    "/automations/from-description",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    }
  );

export const pauseAutomation = (id: string) =>
  j<Automation>(`/automations/${id}/pause`, { method: "POST" });
export const resumeAutomation = (id: string) =>
  j<Automation>(`/automations/${id}/resume`, { method: "POST" });
export const runAutomation = (id: string) =>
  j<Run>(`/automations/${id}/run`, { method: "POST" });
export const deleteAutomation = (id: string) =>
  j<{ deleted: string }>(`/automations/${id}`, { method: "DELETE" });
export const listRuns = (id: string) =>
  j<{ runs: Run[] }>(`/automations/${id}/runs`).then((r) => r.runs);

// ---------------------------------------------------------------- chat

export type ChatResponse = {
  intent: "build" | "suggest" | "ask";
  reply: string;
  created_automation?: Automation;
  suggestions?: Opportunity[];
  automations?: Automation[];
  metrics?: DiscoveryResult["metrics"];
  parsed?: Record<string, unknown>;
};

export const chat = (message: string) =>
  j<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

// ---------------------------------------------------------------- rework (data)

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

export const getReworkReport = () => j<ReworkReport>("/rework/report");

// ---------------------------------------------------------------- connections (OAuth)

export type Connection = {
  provider: string;   // google | slack | github | jira
  label: string;
  configured: boolean; // client id/secret present in the API's env
  connected: boolean;  // a token is stored
  account: string;
  scope: string;
};

export const getConnections = () =>
  j<{ connections: Connection[] }>("/auth/connections").then((r) => r.connections);

export const disconnectProvider = (provider: string) =>
  j<{ ok: boolean; provider: string }>(`/auth/${provider}/disconnect`, { method: "POST" });

// Connect is a server-side redirect, so it must be a real navigation (an <a href>), not fetch.
export const loginUrl = (provider: string) => `${API_BASE}/auth/${provider}/login`;
