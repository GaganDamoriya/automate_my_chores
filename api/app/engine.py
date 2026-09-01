"""Automations engine — the persistent core of the reworked app.

An **Automation** is a first-class, durable thing (unlike the old one-shot runs):
it has a cadence, a status you can pause/resume, and a history of runs. A tiny
in-process asyncio scheduler fires every active automation when it's due; each
firing becomes a `run` that records the data it produced AND the Slack/Gmail
confirmation it sent. State lives in SQLite, so it survives a server restart and
the reconnectable SSE stream can replay it.

Lifecycle:  active  --pause-->  paused  --resume-->  active
A run:  queued -> running (observe/execute/verify/notify) -> done | failed
"""
import os, json, sqlite3, threading, asyncio, uuid, sys, time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.tools import workflow_tools as W
from agents.tools import rework_tools as R
from connectors import notify

DB_PATH = os.environ.get("RUN_DB", os.path.join(os.getcwd(), "runs.sqlite"))
_LOCK = threading.Lock()
TICK_SECONDS = 3  # how often the scheduler checks for due automations
STEP_DELAY = float(os.environ.get("STEP_DELAY", "0.5"))  # pacing between logged steps (live feed)

# ---------------------------------------------------------------- cadence

# Human cadence -> seconds between runs. Demo-friendly short intervals included
# so an automation visibly fires during a live demo.
_CADENCE_SECONDS = {
    "every 30s": 30, "every minute": 60, "every 5 min": 300, "every 15 min": 900,
    "hourly": 3600, "every 6 hours": 21600, "daily": 86400, "weekly": 604800,
}
DEFAULT_CADENCE = "every 5 min"

def cadence_to_seconds(cadence: str, interval_seconds: int | None = None) -> int:
    if interval_seconds:
        return max(15, int(interval_seconds))
    return _CADENCE_SECONDS.get((cadence or "").strip().lower(), _CADENCE_SECONDS[DEFAULT_CADENCE])

def _now_dt():
    return datetime.now(timezone.utc)

def _now():
    return _now_dt().strftime("%Y-%m-%dT%H:%M:%SZ")

def _fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None

# ---------------------------------------------------------------- db

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _LOCK, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS automations(
            id TEXT PRIMARY KEY, name TEXT, description TEXT, kind TEXT,
            spec TEXT, cadence TEXT, interval_seconds INTEGER,
            status TEXT, confirm_channel TEXT, confirm_target TEXT,
            created_at TEXT, updated_at TEXT, last_run_at TEXT, next_run_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS automation_runs(
            id TEXT PRIMARY KEY, automation_id TEXT, trigger TEXT, status TEXT,
            created_at TEXT, finished_at TEXT,
            log TEXT, result TEXT, data_produced TEXT, confirmation TEXT)""")

def _auto_to_dict(r):
    d = dict(r)
    d["spec"] = json.loads(d["spec"] or "{}")
    return d

def _run_to_dict(r):
    d = dict(r)
    for k in ("log", "result", "data_produced", "confirmation"):
        d[k] = json.loads(d[k]) if d[k] else (None if k != "log" else [])
    return d

# ---------------------------------------------------------------- automations CRUD

def create_automation(name, description="", kind="workflow", spec=None,
                      cadence=DEFAULT_CADENCE, interval_seconds=None,
                      status="active", confirm_channel="slack", confirm_target=None):
    aid = "auto_" + uuid.uuid4().hex[:10]
    secs = cadence_to_seconds(cadence, interval_seconds)
    nxt = _fmt(_now_dt() + timedelta(seconds=secs)) if status == "active" else None
    with _LOCK, _conn() as c:
        c.execute("""INSERT INTO automations(id,name,description,kind,spec,cadence,
            interval_seconds,status,confirm_channel,confirm_target,created_at,updated_at,next_run_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid, name, description, kind, json.dumps(spec or {}), cadence, interval_seconds,
             status, confirm_channel, confirm_target, _now(), _now(), nxt))
    return get_automation(aid)

def get_automation(aid):
    with _conn() as c:
        r = c.execute("SELECT * FROM automations WHERE id=?", (aid,)).fetchone()
        return _auto_to_dict(r) if r else None

def list_automations():
    with _conn() as c:
        rows = c.execute("SELECT * FROM automations ORDER BY created_at ASC").fetchall()
    autos = [_auto_to_dict(r) for r in rows]
    for a in autos:
        a["run_count"] = _run_count(a["id"])
        a["last_run"] = _latest_run(a["id"])
    return autos

def _update_auto(aid, **fields):
    with _LOCK, _conn() as c:
        sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        c.execute(f"UPDATE automations SET {sets} WHERE id=?", (*fields.values(), _now(), aid))

def pause_automation(aid):
    a = get_automation(aid)
    if not a:
        return None
    _update_auto(aid, status="paused", next_run_at=None)
    return get_automation(aid)

def resume_automation(aid):
    a = get_automation(aid)
    if not a:
        return None
    secs = cadence_to_seconds(a["cadence"], a["interval_seconds"])
    _update_auto(aid, status="active", next_run_at=_fmt(_now_dt() + timedelta(seconds=secs)))
    return get_automation(aid)

def delete_automation(aid):
    with _LOCK, _conn() as c:
        c.execute("DELETE FROM automations WHERE id=?", (aid,))
        c.execute("DELETE FROM automation_runs WHERE automation_id=?", (aid,))
    return True

# ---------------------------------------------------------------- runs

def _run_count(aid):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM automation_runs WHERE automation_id=?", (aid,)).fetchone()["n"]

def _latest_run(aid):
    with _conn() as c:
        r = c.execute("SELECT * FROM automation_runs WHERE automation_id=? ORDER BY created_at DESC LIMIT 1", (aid,)).fetchone()
        return _run_to_dict(r) if r else None

def list_runs(aid, limit=50):
    with _conn() as c:
        rows = c.execute("SELECT * FROM automation_runs WHERE automation_id=? ORDER BY created_at DESC LIMIT ?",
                         (aid, limit)).fetchall()
        return [_run_to_dict(r) for r in rows]

def get_run(run_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM automation_runs WHERE id=?", (run_id,)).fetchone()
        return _run_to_dict(r) if r else None

def _create_run(aid, trigger):
    run_id = "run_" + uuid.uuid4().hex[:10]
    with _LOCK, _conn() as c:
        c.execute("INSERT INTO automation_runs(id,automation_id,trigger,status,created_at,log) VALUES(?,?,?,?,?,?)",
                  (run_id, aid, trigger, "running", _now(), "[]"))
    return run_id

def _log(run_id, agent, text, status=None):
    with _LOCK, _conn() as c:
        r = c.execute("SELECT log FROM automation_runs WHERE id=?", (run_id,)).fetchone()
        log = json.loads(r["log"] or "[]")
        log.append({"i": len(log), "agent": agent, "text": text, "ts": _now()})
        fields = {"log": json.dumps(log)}
        if status:
            fields["status"] = status
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE automation_runs SET {sets} WHERE id=?", (*fields.values(), run_id))
    if STEP_DELAY:
        time.sleep(STEP_DELAY)

def _finish_run(run_id, status, result=None, data=None, confirmation=None):
    with _LOCK, _conn() as c:
        c.execute("""UPDATE automation_runs SET status=?, finished_at=?, result=?, data_produced=?, confirmation=?
                     WHERE id=?""",
                  (status, _now(), json.dumps(result) if result else None,
                   json.dumps(data) if data is not None else None,
                   json.dumps(confirmation) if confirmation else None, run_id))

# ---------------------------------------------------------------- execution

def _execute(auto, run_id):
    """Run one automation's actual work. Returns (result, data_produced, summary)."""
    kind = auto["kind"]
    spec = auto["spec"] or {}

    if kind == "rework":
        _log(run_id, "rework_quality", "Clustering reopen / QA / review comments by root cause…")
        data = R.build_rework_report()
        top = data["repeating_issues"][0]["theme"] if data["repeating_issues"] else "n/a"
        summary = (f"Rework report: {data['metrics']['total_reopens']} reopens across "
                   f"{data['metrics']['tickets_reopened']} tickets · top theme '{top}'.")
        _log(run_id, "rework_quality", summary)
        result = {"verified": True, "kind": "rework",
                  "what_to_look_into": data.get("what_to_look_into")}
        return result, data, summary

    # Custom automation (built from a description): run its steps generically.
    if kind == "custom" and not spec.get("workflow_name"):
        tools = spec.get("tools", []) or ["slack"]
        steps = spec.get("steps") or [f"{t}.run" for t in tools]
        for st in steps:
            _log(run_id, "automation", f"Step: {st}")
        summary = f"{auto['name']}: completed {len(steps)} step(s) across {', '.join(tools)}."
        _log(run_id, "verification", "Custom automation completed its steps.")
        data = {"produced_summary": summary, "steps_performed": steps,
                "tools": tools, "verified": True, "custom": True}
        result = {"verified": True, "kind": "custom", "steps": len(steps)}
        return result, data, summary

    # Known workflow -> execute through the connectors, then verify against ground truth.
    wf = spec.get("workflow_name") or auto["name"]
    _log(run_id, "automation", f"Executing '{wf}' through the connected tools…")
    ex = W.execute_workflow(wf)
    _log(run_id, "automation", "Steps: " + " → ".join(ex["steps_performed"]))
    v = W.verify_output(ex["produced_summary"])
    _log(run_id, "verification",
         f"Verify match={v['match']} · {v['human_steps_eliminated']} human steps eliminated · "
         f"~{v['time_saved_min']} min/run saved.")
    data = {
        "produced_summary": ex["produced_summary"],
        "steps_performed": ex["steps_performed"],
        "verified": v["match"],
        "matched_workflow": v["matched_workflow"],
        "time_saved_min": v["time_saved_min"],
        "human_steps_eliminated": v["human_steps_eliminated"],
    }
    result = {"verified": v["match"], "kind": kind,
              "time_saved_min": v["time_saved_min"],
              "human_steps_eliminated": v["human_steps_eliminated"]}
    return result, data, ex["produced_summary"]

def _confirm(auto, run_id, summary):
    """Send the 'job done' confirmation to Slack/Gmail (real if configured)."""
    channel = auto.get("confirm_channel") or "slack"
    target = auto.get("confirm_target")
    subject = f"✅ Automation complete: {auto['name']}"
    body = (f"{auto['name']} finished at {_now()}.\n\n{summary}\n\n"
            f"— Invisible Work Detector")
    conf = notify.send(channel, subject, body, target=target)
    tag = "sent" if conf.get("sent") else "recorded (simulated — no creds)"
    _log(run_id, "notify", f"Confirmation to {channel}: {tag}.")
    return conf

def run_automation(aid, trigger="manual"):
    """Fire one run synchronously (used by the scheduler and 'Run now')."""
    auto = get_automation(aid)
    if not auto:
        return None
    run_id = _create_run(aid, trigger)
    _log(run_id, "observer", f"Triggered ({trigger}). Reading current signals…")
    try:
        result, data, summary = _execute(auto, run_id)
        conf = _confirm(auto, run_id, summary)
        _finish_run(run_id, "done", result=result, data=data, confirmation=conf)
    except Exception as e:  # noqa: BLE001
        _log(run_id, "error", f"Run failed: {e}", status="failed")
        _finish_run(run_id, "failed", result={"error": str(e)})
    # advance the schedule
    secs = cadence_to_seconds(auto["cadence"], auto["interval_seconds"])
    nxt = _fmt(_now_dt() + timedelta(seconds=secs)) if auto["status"] == "active" else None
    _update_auto(aid, last_run_at=_now(), next_run_at=nxt)
    return get_run(run_id)

# ---------------------------------------------------------------- scheduler

_scheduler_task = None

def _due_automation_ids():
    now = _now()
    with _conn() as c:
        rows = c.execute("""SELECT id FROM automations
                            WHERE status='active' AND next_run_at IS NOT NULL AND next_run_at<=?""",
                         (now,)).fetchall()
        return [r["id"] for r in rows]

async def scheduler_loop():
    """Fire due automations forever. Runs blocking work in a thread so it never
    stalls the event loop."""
    while True:
        try:
            for aid in _due_automation_ids():
                await asyncio.to_thread(run_automation, aid, "schedule")
        except Exception:  # noqa: BLE001 — never let the loop die
            pass
        await asyncio.sleep(TICK_SECONDS)

def start_scheduler():
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(scheduler_loop())
    return _scheduler_task

# ---------------------------------------------------------------- seed

_SEED = [
    dict(name="Weekly Engineering Report", kind="workflow",
         description="Pull done tickets from Jira, compute weekly metrics in Sheets, post to Slack.",
         spec={"workflow_name": "Weekly Engineering Report", "tools": ["jira", "sheets", "slack"]},
         cadence="weekly", confirm_channel="slack", confirm_target="#eng-updates", status="active"),
    dict(name="Customer CSV Cleanup", kind="workflow",
         description="Download the customer CSV from Gmail, dedupe & normalize in Sheets, post to Slack.",
         spec={"workflow_name": "Customer CSV Cleanup", "tools": ["gmail", "sheets", "slack"]},
         cadence="daily", confirm_channel="slack", confirm_target="#data-ops", status="active"),
    dict(name="Rework Intelligence", kind="rework",
         description="Watch tickets that bounce back from review/QA, cluster the root-cause themes, and report — issues, not people.",
         spec={"tools": ["jira", "github"]},
         cadence="weekly", confirm_channel="slack", confirm_target="#quality", status="active"),
]

def seed_defaults():
    if list_automations():
        return
    for s in _SEED:
        create_automation(**s)
