# Invisible Work Detector

**A multi-agent system that finds the repetitive "invisible work" hiding in a team's tools, turns it into a running automation, and keeps those automations working for you — start, stop, and restart them anytime.**

Built for the **All Things Agentic** hackathon (Taskmaster track) on **Google ADK + Gemini + Google Cloud (Vertex AI)**.

> _"We don't watch people. We watch workflows."_

Most productivity tools measure output. Invisible Work Detector measures the *hidden cost of repetition* — the weekly report someone rebuilds by hand, the CSV they clean every Monday, the tickets that keep bouncing back from QA — and then automates it and runs it on a schedule, confirming to you (in Slack or Gmail) every time it does the job.

---

## The idea

1. **A chain of master agents watches your workflows** and surfaces where automation is worth it.
2. **Creating an automation is as easy as describing it** — type it into the dashboard chat bar and it's built.
3. **Custom automations from a plain-English description** — no config, no wiring.
4. **An Automations page shows everything currently running** — with live status you can **Stop** or **Restart** at any moment.
5. **Every automation records what it did and everything it sent**, and posts a **Slack / Gmail confirmation** when it finishes.

Rework intelligence isn't a separate screen — it's just **one of the automations**.

---

## How it works

**The dashboard leads with a chat/search bar.** Describe what you want ("every morning post a Jira digest to #standup") and the **Master → Builder** agents turn it into a running automation. Ask "what can I automate?" and the **Watcher chain** (Observer → Pattern → Analyst) surfaces the invisible work it found, each with a one-tap **Automate** button.

**An automation is a persistent, scheduled thing.** It has a cadence, a live status, and a run history. A tiny in-process scheduler fires each active automation when it's due; every firing is a **run** that records the data it produced and the confirmation it sent. **Stop** pauses the schedule; **Restart** resumes it — instantly, anytime.

**It tells you it did the job.** When a run finishes it sends a confirmation to **Slack** (incoming webhook) or **Gmail** (SMTP). Configure the credentials and messages post for real; leave them blank and every message is still *recorded* (marked `simulated`) so the demo never breaks.

---

## Agents

- **Master** (`agents/master.py`) — routes a chat message to an intent: *build* an automation, *suggest* opportunities, or *ask*.
- **Builder** (`agents/builder.py`) — turns a plain-English description into a structured automation spec (name, kind, cadence, tools, confirmation channel). Pure-Python by default; real Gemini on the ADK path.
- **Watcher chain** (`observer → pattern → analyst`) — noise-robust discovery of repeated cross-tool workflows, orchestrated as an ADK `SequentialAgent`.
- **Executor + Verification** — runs a workflow through the connectors and verifies its output against a known-good result.
- **Rework** — clusters reopened/QA tickets into root-cause themes (issues, not people). Now runs as the seeded **Rework Intelligence** automation.

---

## Architecture

```
automate_my_chores/
  agents/        Google ADK agents
    master.py      chat intent router
    builder.py     description -> automation spec
    observer/pattern/analyst/automation/verification/rework
    tools/         the real, runnable function-tools the agents call
  api/app/
    engine.py      persistent automations + runs + the scheduler   <-- reworked core
    routers/       automations, chat, discovery, rework, activity
  connectors/
    notify.py      real Slack + Gmail confirmations (gated, stdlib) <-- new
    gmail/jira/github/sheets/slack (read the seed, write to a sink)
  seed/          simulated activity generator (stdlib) + generated data/
  web/           Next.js + Tailwind
    app/page.tsx           chat-first dashboard
    app/automations/       the Automations page (status, stop/restart, run history)
    components/            ChatBar, SuggestionCard, AutomationCard, RunHistory
```

**Real vs. simulated.** Discovery, scoring, execution, verification, rework clustering, the scheduler, and (with creds) the Slack/Gmail sends are all real. Only the *activity source* is simulated seed data, which keeps the demo deterministic and free of live-API risk.

---

## Quick start

```bash
cp .env.example .env        # fill in Slack/Gmail creds to send for real (optional)
make seed                   # simulated activity -> seed/data/*.json
make install-api && make api   # http://localhost:8000  (terminal 1)
make install-web && make web   # http://localhost:3000  (terminal 2)
```

On first boot the API seeds three automations (Weekly Engineering Report, Customer CSV Cleanup, Rework Intelligence) and starts the scheduler. Open the dashboard, describe an automation in the chat bar, then watch it on the **Automations** page.

### Real Slack + Gmail confirmations

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your-16-char-google-app-password
GMAIL_TO=where-to-send@example.com          # optional; defaults to GMAIL_ADDRESS
```

Leave them blank to keep confirmations simulated (recorded, not sent). The Gmail password must be a Google **App Password**, not your login password.


---

## Connect your tools (OAuth)

Beyond the static Slack webhook / Gmail app-password, you can authorize tools with **OAuth**
from the **Connections** page — automations then act through granted scopes, and fall back to
simulation when a provider isn't connected.

| Provider | What it enables | Register at | Scopes |
| --- | --- | --- | --- |
| **Google** | Real Gmail send + Sheets append | Cloud Console → Credentials → OAuth client (Web) | `gmail.send`, `spreadsheets`, `email` |
| **Slack** | Bot posts confirmations to any channel | api.slack.com/apps → OAuth & Permissions | `chat:write`, `channels:read` |
| **GitHub** | Real PR reviews as a rework source | Developer settings → OAuth Apps | `repo`, `read:user` |
| **Jira** | Real tickets for discovery / rework | developer.atlassian.com → OAuth 2.0 (3LO) | `read:jira-work`, `offline_access` |

For each app, set the redirect URI to `http://localhost:8000/auth/<provider>/callback` and put the
client id/secret in `.env` (see `.env.example`). Then open **/connections**, click **Connect**,
and authorize. Tokens are stored locally (single-user), refreshed automatically for Google/Jira.
Nothing configured? Everything still runs on the simulated fallback.

---

## API

```
# Automations (the core)
GET    /automations                     list all, with status + last run
POST   /automations                     create from a full spec (the Automate button)
POST   /automations/from-description    build from plain English
GET    /automations/{id}                one automation + its runs
POST   /automations/{id}/run            fire it now
POST   /automations/{id}/pause          Stop
POST   /automations/{id}/resume         Restart
DELETE /automations/{id}
GET    /automations/{id}/runs           run history (data produced + confirmations)
GET    /automations/{id}/stream         reconnectable SSE of the latest run

# Chat / search bar
POST   /chat                            {message} -> build | suggest | ask

# Discovery + rework data
GET    /discovery/suggestions           invisible-work opportunities
GET    /rework/report                   rework report (data for the Rework automation)
GET    /activity/stream                 live agent feed (SSE)
```

---

## Running the real agents on Vertex AI

The agents run on **Gemini via Vertex AI**, authenticated with Application Default Credentials.

```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT
gcloud auth application-default set-quota-project YOUR_PROJECT
```

Set in `.env`:

```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash
USE_ADK=1
```

```bash
make install-agents
python -m agents.run_local     # full ADK watcher pipeline, live feed in the terminal
```

The agents call the exact same tools the API uses, so the structured metrics stay reliable while Gemini supplies the reasoning.

---

## Tech stack

**Backend** FastAPI · SSE · SQLite-backed automations engine + in-process scheduler · stdlib Slack/Gmail connectors
**Agents** Google ADK (`SequentialAgent` + `LlmAgent`) · Gemini on Vertex AI · function-tools
**Frontend** Next.js · React · Tailwind CSS

## Roadmap

- Cloud-native deploy: Cloud Scheduler + Cloud SQL (`DatabaseSessionService`) + Cloud Run.
- Expand connectors from simulated sources to live, authorized integrations.
- Per-run diff view and richer confirmation templates.
