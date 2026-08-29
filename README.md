# Invisible Work Detector

An autonomous AI agent that discovers repetitive, manual **"invisible work"** inside
organizations and turns it into automation — built for the **All Things Agentic**
hackathon (Taskmaster track) on **Gemini + Google ADK + Google Cloud**.

> "We don't watch people. We watch workflows."

The agent runs one complete autonomous loop:
**observe → discover → understand → plan → automate → execute → verify → measure**,
plus a second **rework & quality** lane that mines Jira reopens and GitHub review
comments into a weekly report.

See the full build blueprint (architecture, agents, demo script) shared separately.

## Layout

```
automate_my_chores/
  agents/        Google ADK agents (Observer, Pattern, Analyst, Automation, Verification, Rework)
    tools/       real, runnable function-tools the agents call
  api/           FastAPI backend (REST + SSE) over the agent tools
  connectors/    mock Gmail / Jira / GitHub / Sheets / Slack (read seed, write to sink)
  seed/          simulated activity generator (stdlib) + generated data/
  web/           Next.js + Tailwind dashboard
```

## Quick start

```bash
# 0. one-time: put your key in .env  (copy from .env.example)
cp .env.example .env        # set GEMINI_API_KEY, GEMINI_MODEL

# 1. generate the simulated organization's activity
make seed                   # -> seed/data/*.json

# 2. backend  (terminal 1)
make install-api
make api                    # http://localhost:8000  (/health, /discovery/run, /rework/report, /activity/stream)

# 3. frontend (terminal 2)
make install-web
make web                    # http://localhost:3000
```

The backend runs today on the pure-Python tools (no Gemini key required to see the
loop). To run the **real ADK pipeline**, install `google-adk`, set `GEMINI_API_KEY`,
and invoke `agents.root_agent:root_agent` with an ADK Runner — the tools are already
wired to the agents.

## What's real vs simulated

Real: pattern discovery, effort/opportunity scoring, execution through the connectors,
output verification, and rework-theme clustering — all run on actual logic. Simulated:
only the *activity source* (seed data), so the demo has zero live-API risk.

## Running the real ADK agents

By default the backend serves discovery from the deterministic tools (no key needed),
so the loop and dashboard work offline. To run the **real Gemini agents** via ADK:

```bash
pip install google-adk google-genai
export GEMINI_API_KEY=...        # AI Studio key
export USE_ADK=1
```

- `GET /activity/stream` then streams **live agent events** (each tool call and each
  agent's reasoning) instead of the scripted narration.
- `POST /discovery/analyze` runs the full pipeline and returns the agents' final
  reasoning plus session state.
- Terminal demo: `python -m agents.run_local` prints the live feed.

The agents call the same tools the API uses, so structured metrics stay reliable
while Gemini provides the reasoning, recommendations, and the "why".

## Run on Vertex AI (uses Google Cloud credits, higher quota)

Vertex uses your Cloud login (ADC) + a project/region — no API key. One-time setup:

```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT
gcloud auth application-default set-quota-project YOUR_PROJECT
```

Set in .env (already scaffolded — confirm the values):
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash
```

Then (inside the venv, after re-sourcing .env):
```bash
python3 scripts/validate_gemini.py     # validates via google-genai on Vertex
python -m agents.run_local             # full ADK pipeline on Vertex
```

## Autonomy: async runs & the approval gate

The Taskmaster proof — a run executes server-side and its every step is persisted,
so it survives the client disconnecting and pauses for human approval before acting.

```
POST /events/ingest        # Pub/Sub-style trigger: "new activity detected" -> starts a run
POST /runs                 # start a run manually (returns immediately)
GET  /runs/{id}            # durable state (call after reconnecting)
GET  /runs/{id}/stream     # reconnectable SSE: replays the log, then tails it
POST /runs/{id}/approve    # approve the gate -> run resumes (execute -> verify)
```

Lifecycle: `queued → observing → discovering → analyzing → awaiting_approval → executing → verifying → done`.
The gate sits before `executing`; the run will not act until approved.

**Demo the "it keeps working" moment:** press *Detect & run* on the dashboard, then
**close the tab** while it runs. Reopen it — the run advanced on its own and is waiting
at the approval gate (state is persisted in SQLite; Cloud SQL in production, via ADK's
`DatabaseSessionService`). Press *Approve & execute* to finish.

## Validate the Gemini key/model (run on your own machine)

> **Gemini free tier = 5 requests/min.** The 5-agent pipeline makes ~12 calls, so a
> free-tier key hits `429 RESOURCE_EXHAUSTED` mid-run (this is expected, not a bug —
> the agents run correctly up to the cap). For an uninterrupted end-to-end run, enable
> billing on the key (paid tier lifts the limit). `run_local` now reports this cleanly.


Both cloud sandboxes used to build this block the Gemini API host, so validation
must run where you have open internet. Two ways:

```bash
# A) Zero-install REST check — key + model + function-calling (no pip needed)
python3 scripts/validate_gemini.py        # or: make validate

# B) Full ADK pipeline through Gemini
pip install google-adk google-genai
export USE_ADK=1
python -m agents.run_local
```

If (A) 404s on the model, set GEMINI_MODEL=gemini-2.5-flash and retry.

## Status

Scaffold + working discovery/rework logic + data generator + API + dashboard shell.
Model: `gemini-3.5-flash` (stable) or `gemini-3.7-flash` (newer, agentic-tuned) via env.
