"""Durable, resumable run engine — the Taskmaster autonomy core.

A "run" is a discovery→automation job that executes in a server-side background
task while every state transition is persisted to SQLite. Because progress lives
in the DB (not the HTTP connection), a run keeps going after the user closes the
tab, and reconnecting replays the durable state. The run pauses at an
`awaiting_approval` gate and only resumes when `approve()` is called — the local
analog of ADK's long-running tool / webhook-resume (Cloud SQL in production).
"""
import os, json, sqlite3, threading, asyncio, uuid
from datetime import datetime, timezone
from . import service

DB_PATH = os.environ.get("RUN_DB", os.path.join(os.getcwd(), "runs.sqlite"))
_LOCK = threading.Lock()

# Lifecycle. The gate sits between ANALYZING and EXECUTING.
BEFORE_GATE = [
    ("observer", "observing", "Reading activity log across Gmail, Jira, GitHub, Sheets, Slack…"),
    ("pattern_detection", "discovering", "Mining for repeated cross-tool workflows…"),
    ("workflow_analyst", "analyzing", "Estimating effort and scoring automatability…"),
]
AFTER_GATE = [
    ("automation", "executing", "Executing the approved workflow through the tools…"),
    ("verification", "verifying", "Comparing produced output to expected…"),
]

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _LOCK, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, trigger TEXT, status TEXT,
            created_at TEXT, updated_at TEXT,
            opportunity_id TEXT, opportunity_name TEXT,
            log TEXT, result TEXT, approved INTEGER DEFAULT 0)""")

def _row_to_dict(r):
    d = dict(r)
    d["log"] = json.loads(d["log"] or "[]")
    d["result"] = json.loads(d["result"]) if d["result"] else None
    d["approved"] = bool(d["approved"])
    return d

def get_run(run_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return _row_to_dict(r) if r else None

def list_runs(limit=25):
    with _conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_dict(r) for r in rows]

def create_run(trigger="manual"):
    run_id = "run_" + uuid.uuid4().hex[:10]
    with _LOCK, _conn() as c:
        c.execute("INSERT INTO runs(id,trigger,status,created_at,updated_at,log) VALUES(?,?,?,?,?,?)",
                  (run_id, trigger, "queued", _now(), _now(), "[]"))
    return run_id

def _update(run_id, **fields):
    with _LOCK, _conn() as c:
        sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        c.execute(f"UPDATE runs SET {sets} WHERE id=?",
                  (*fields.values(), _now(), run_id))

def _log(run_id, agent, text, status=None):
    with _LOCK, _conn() as c:
        r = c.execute("SELECT log FROM runs WHERE id=?", (run_id,)).fetchone()
        log = json.loads(r["log"] or "[]")
        log.append({"i": len(log), "agent": agent, "text": text, "ts": _now()})
        fields = {"log": json.dumps(log)}
        if status:
            fields["status"] = status
        sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        c.execute(f"UPDATE runs SET {sets} WHERE id=?", (*fields.values(), _now(), run_id))

def approve(run_id):
    run = get_run(run_id)
    if not run or run["status"] != "awaiting_approval":
        return False
    _update(run_id, approved=1)
    _log(run_id, "human", "Approved by user.")
    return True

async def advance_to_gate(run_id, step_delay=0.9):
    """Phase 1: observe → discover → analyze, then PAUSE at the approval gate."""
    try:
        for agent, status, text in BEFORE_GATE:
            _log(run_id, agent, text, status=status)
            await asyncio.sleep(step_delay)
        disc = service.run_discovery()
        top = disc["opportunities"][0] if disc["opportunities"] else None
        if not top:
            _log(run_id, "workflow_analyst", "No opportunities found.", status="done")
            return
        _update(run_id, opportunity_id=top["id"], opportunity_name=top["name"])
        _log(run_id, "workflow_analyst",
             f"Found '{top['name']}' → ~{top['annual_hours_est']} hrs/yr. "
             f"Recommend {top['recommended_action']}. Awaiting approval.",
             status="awaiting_approval")
    except Exception as e:
        _log(run_id, "error", f"Run failed before gate: {e}", status="failed")

async def execute_after_gate(run_id, step_delay=0.9):
    """Phase 2: resume after approval → execute → verify → done."""
    run = get_run(run_id)
    if not run or run["status"] != "awaiting_approval" or not run["approved"]:
        return
    try:
        for agent, status, text in AFTER_GATE:
            _log(run_id, agent, text, status=status)
            await asyncio.sleep(step_delay)
        result = service.execute(run["opportunity_id"] or "opp_001")
        _update(run_id, result=json.dumps(result))
        _log(run_id, "verification",
             f"Match {result['verified']} · {result['human_steps_eliminated']} human steps "
             f"eliminated · ~{result['time_saved_min']} min/run saved.",
             status="done")
    except Exception as e:
        _log(run_id, "error", f"Run failed after gate: {e}", status="failed")
