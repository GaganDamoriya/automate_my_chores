# Invisible Work Detector

**An autonomous AI agent that finds the repetitive, manual "invisible work" hiding inside a team's tools — and turns it into automation.**

Built for the **All Things Agentic** hackathon (Taskmaster track) on **Google ADK + Gemini + Google Cloud (Vertex AI)**.

> _"We don't watch people. We watch workflows."_

Most productivity tools measure output. Invisible Work Detector measures the *hidden cost of repetition* — the weekly report someone rebuilds by hand, the CSV they clean the same way every Monday, the tickets that keep getting reopened — and then does something about it.

---

## What it does

The agent runs one complete autonomous loop:

**observe → discover → understand → plan → automate → execute → verify → measure**

It watches a stream of workplace activity, discovers repeating multi-step workflows buried in the noise, scores how much time each one costs per year, then executes the automation end-to-end and **verifies its own output** against a known-good result before claiming success.

A second **Rework & Quality** lane mines reopened tickets and review churn into a weekly report — surfacing *process* problems (which stages produce rework, which tickets keep coming back), never grading individuals.

---

## Highlights

- **True multi-agent pipeline** on Google ADK — Observer → Pattern → Analyst → Automation → Verification, orchestrated as a `SequentialAgent`, each step calling real, runnable tools.
- **Noise-robust discovery** — clusters activity by day-set overlap (Jaccard similarity) to isolate a workflow's core steps from surrounding noise, and reports median durations. On the demo data it correctly recovers the *Weekly Eng Report* (~43 hrs/yr) and *CSV Cleanup* (~99 hrs/yr) workflows out of hundreds of mixed events.
- **Executes, then verifies** — `execute_workflow` runs the right flow per opportunity (weekly report: Jira → Sheets → Slack; CSV cleanup: Gmail → Sheets → Slack), and `verify_output` checks the produced result against expected output before reporting the hours saved.
- **Durable autonomous runs with a human approval gate** — a run executes server-side, persists every step, survives the client disconnecting, and pauses for human approval before it acts.
- **Live agent feed** — the dashboard streams each agent's reasoning and every tool call in real time over SSE.

---

## Architecture

```
automate_my_chores/
  agents/        Google ADK agents (Observer, Pattern, Analyst, Automation, Verification, Rework)
    tools/       the real, runnable function-tools the agents call
  api/           FastAPI backend (REST + SSE) exposing the agent loop and durable runs
  connectors/    Gmail / Jira / GitHub / Sheets / Slack (read the seed, write to a sink)
  seed/          simulated activity generator (stdlib) + generated data/
  web/           Next.js + Tailwind dashboard
```

**What's real vs. simulated.** Everything that matters is real: pattern discovery, effort and opportunity scoring, execution through the connectors, output verification, and the rework-theme clustering all run on actual logic and, in the full pipeline, real Gemini reasoning. Only the *activity source* is simulated (seed data), which keeps the demo deterministic and free of live-API risk while every agent decision is genuine.

---

## Quick start

Two terminals — the backend and the dashboard.

```bash
# 0. one-time: copy the environment template and confirm the values
cp .env.example .env

# 1. generate the simulated organization's activity
make seed                   # -> seed/data/*.json

# 2. backend  (terminal 1)
make install-api
make api                    # http://localhost:8000

# 3. frontend (terminal 2)
make install-web
make web                    # http://localhost:3000
```

Open **http://localhost:3000** for the dashboard, or hit the API directly at
`http://localhost:8000` (`/health`, `/discovery/run`, `/rework/report`, `/activity/stream`).

The loop and dashboard run on the deterministic tools out of the box, so you can see the full experience without any cloud setup. To bring the real Gemini agents online, follow the Vertex AI setup below.

---

## Running the real agents on Vertex AI

The pipeline runs on **Gemini 2.5 Flash via Vertex AI**, authenticated with your Google Cloud login (Application Default Credentials) — no standalone API key to manage, and production-grade quota.

One-time setup:

```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT
gcloud auth application-default set-quota-project YOUR_PROJECT
```

Set these in `.env` (already scaffolded — confirm the project and region):

```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash
USE_ADK=1
```

Then install the agent dependencies and run:

```bash
make install-agents          # google-adk + google-genai
python3 scripts/validate_gemini.py   # quick end-to-end check via Vertex  (or: make validate)
python -m agents.run_local           # full ADK pipeline, live feed in the terminal
```

With `USE_ADK=1`, the API serves live agents instead of the scripted path:

- `GET /activity/stream` streams **live agent events** — each agent's reasoning and every tool call.
- `POST /discovery/analyze` runs the full pipeline and returns the agents' final reasoning plus session state.

The agents call the exact same tools the API uses, so the structured metrics stay reliable while Gemini supplies the reasoning, the recommendations, and the "why."

---

## Autonomy: durable runs & the approval gate

This is the Taskmaster proof — a run keeps working on its own and won't take action without a human's sign-off.

```
POST /events/ingest        # trigger: "new activity detected" -> starts a run
POST /runs                 # start a run manually (returns immediately)
GET  /runs/{id}            # durable state (call after reconnecting)
GET  /runs/{id}/stream     # reconnectable SSE: replays the log, then tails it
POST /runs/{id}/approve    # approve the gate -> run resumes (execute -> verify)
```

Lifecycle:

```
queued → observing → discovering → analyzing → awaiting_approval → executing → verifying → done
```

The gate sits right before `executing`; the run will not act until it's approved.

**Try the "it keeps working" moment:** press **Detect & run** on the dashboard, then **close the tab** while it's running. Reopen it — the run advanced on its own and is now waiting at the approval gate, because state is persisted in SQLite (Cloud SQL in production, via ADK's `DatabaseSessionService`). Press **Approve & execute** to finish the loop.

---

## Tech stack

**Backend** FastAPI · Server-Sent Events · SQLite-backed durable run engine · Pub/Sub-style event ingestion
**Agents** Google ADK (`SequentialAgent` + `LlmAgent`) · Gemini 2.5 Flash on Vertex AI · function-tools
**Frontend** Next.js · React · Tailwind CSS
**Data** stdlib activity generator; connectors for Gmail, Jira, GitHub, Sheets, and Slack

---

## Roadmap

- Cloud-native deploy: Cloud Pub/Sub + Cloud SQL (`DatabaseSessionService`) + Cloud Run.
- Wire the dashboard's per-opportunity **Automate** action to the durable `/runs` flow.
- Expand the connector set from simulated sources to live, authorized integrations.
