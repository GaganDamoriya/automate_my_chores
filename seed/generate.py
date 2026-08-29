"""
Invisible Work Detector — simulated activity generator.

Produces a realistic-but-fake event log for a fictional org so the agents have
something to DISCOVER. Only the data source is simulated; the agents, reasoning,
execution and verification are real.

Outputs (seed/data/):
  activity_events.json  — normalized cross-tool events (the Observer's input)
  ticket_events.json    — Jira ticket lifecycle incl. reopens / QA fails
  review_comments.json  — GitHub PR reviews + QA comments (the rework signal)
  ground_truth.json     — what a perfect agent SHOULD find (for evaluation only)

Deterministic: seeded, anchored to a fixed reference Monday, stdlib only.
Run:  python3 seed/generate.py
"""
import json, random, os
from datetime import datetime, timedelta, date

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)

REFERENCE_MONDAY = datetime(2026, 8, 24, 9, 0)  # "week of Aug 24"
WEEKS = 10

_eid = 0
def eid(prefix):
    global _eid
    _eid += 1
    return f"{prefix}_{_eid:05d}"

def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

activity = []

def emit_run(start, actor, steps):
    """steps: list of (tool, action, artifact, minute_offset)."""
    for tool, action, artifact, off in steps:
        activity.append({
            "id": eid("evt"),
            "actor": actor,
            "tool": tool,
            "action": action,
            "artifact": artifact,
            "ts": iso(start + timedelta(minutes=off)),
        })

# --- Workflow A: Weekly Engineering Report (Mondays ~09:00, ~52 min) ---
WEEKLY_REPORT = [
    ("gmail",  "download_attachment", "eng_report.csv",       0),
    ("jira",   "run_jql",             "status=Done AND sprint=current", 6),
    ("sheets", "open_spreadsheet",    "Eng Weekly Metrics",   10),
    ("sheets", "paste_values",        "Eng Weekly Metrics",   18),
    ("sheets", "compute_formula",     "weekly_totals",        31),
    ("slack",  "post_message",        "#eng-updates",         50),
]
for w in range(WEEKS):
    monday = REFERENCE_MONDAY - timedelta(weeks=(WEEKS - 1 - w))
    jitter = random.randint(-6, 9)
    emit_run(monday + timedelta(minutes=jitter), "emp_ally", WEEKLY_REPORT)

# --- Workflow B: Customer CSV Cleanup (~4x/week, ~31 min) ---
CSV_CLEANUP = [
    ("gmail",  "download_attachment", "customers_batch.csv",  0),
    ("sheets", "open_spreadsheet",    "Customer Master",      3),
    ("sheets", "dedupe_rows",         "Customer Master",      12),
    ("sheets", "normalize_columns",   "Customer Master",      20),
    ("sheets", "export_csv",          "customers_clean.csv",  27),
    ("slack",  "post_message",        "#data-ops",            30),
]
for w in range(WEEKS):
    week_start = REFERENCE_MONDAY - timedelta(weeks=(WEEKS - 1 - w))
    for d in random.sample([0, 1, 2, 3, 4], k=random.choice([3, 4, 4, 4])):
        day = week_start + timedelta(days=d, hours=random.randint(1, 6))
        emit_run(day + timedelta(minutes=random.randint(-5, 5)), "emp_ben", CSV_CLEANUP)

# --- Decoy noise so discovery is non-trivial ---
NOISE = [
    ("gmail", "read_email"), ("gmail", "send_email"), ("slack", "post_message"),
    ("jira", "add_comment"), ("jira", "transition_issue"), ("sheets", "open_spreadsheet"),
    ("github", "push_commit"), ("github", "open_pr"), ("calendar", "create_event"),
]
noise_actors = ["emp_ally", "emp_ben", "emp_cara", "emp_dev", "emp_ell"]
for _ in range(220):
    tool, action = random.choice(NOISE)
    dt = REFERENCE_MONDAY - timedelta(
        weeks=random.randint(0, WEEKS - 1),
        days=random.randint(0, 6),
        hours=random.randint(0, 8),
        minutes=random.randint(0, 59),
    )
    activity.append({
        "id": eid("evt"),
        "actor": random.choice(noise_actors),
        "tool": tool,
        "action": action,
        "artifact": random.choice(["misc", "adhoc", "thread", "PROJ", "sheet"]),
        "ts": iso(dt),
    })

activity.sort(key=lambda e: e["ts"])

# --- Rework & Quality lane: Jira reopens + GitHub review comments ---
THEMES = {
    "missing_tests": [
        "No test coverage for the empty-input case.",
        "Please add a unit test for the null response path.",
        "This needs a regression test before we merge.",
        "Edge cases aren't covered — what happens with an empty list?",
    ],
    "spec_misunderstanding": [
        "This isn't what the ticket asked for — see acceptance criteria #2.",
        "Requirement was pagination, not infinite scroll.",
        "Totals should exclude refunds per the spec.",
    ],
    "null_handling": [
        "Unhandled null when the API returns no data.",
        "NullPointer risk on user.profile when the profile is missing.",
    ],
    "error_handling": [
        "This swallows the exception and hides real failures.",
        "Need retry/backoff on the 5xx path.",
    ],
    "flaky_test": [
        "Test fails intermittently on CI — it's timing dependent.",
        "Flaky: relies on a wall-clock sleep.",
    ],
    "style": [
        "Naming and readability nits, see inline comments.",
        "Extract this into a helper for clarity.",
    ],
}
# Weighted so 'missing_tests' is the dominant repeating issue.
THEME_WEIGHTS = (
    ["missing_tests"] * 6 + ["spec_misunderstanding"] * 4 + ["null_handling"] * 3
    + ["error_handling"] * 2 + ["flaky_test"] * 2 + ["style"] * 1
)
REOPEN_DIST = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 4]  # most tickets clean; a few painful
TITLES = [
    "Export billing CSV", "Login rate limit", "Webhook retry logic", "Search relevance tweak",
    "Invoice PDF layout", "SSO token refresh", "Bulk import validation", "Dashboard date filter",
    "Email digest scheduler", "Refund edge cases", "Audit log pagination", "Feature flag rollout",
    "CSV encoding fix", "Timezone in reports", "Password reset flow", "Rate card calculation",
]
ticket_events, review_comments, ground = [], [], {}
NUM_TICKETS = 28
for i in range(NUM_TICKETS):
    tid = f"PROJ-{440 + i}"
    author = f"dev_{random.choice('abcdef')}"
    created = REFERENCE_MONDAY - timedelta(weeks=random.randint(0, 4),
                                           days=random.randint(0, 4),
                                           hours=random.randint(0, 6))
    ticket_events.append({"id": eid("tk"), "ticket": tid, "title": random.choice(TITLES),
                          "event": "created", "to_status": "Open", "actor": author, "ts": iso(created)})
    cursor = created + timedelta(hours=random.randint(2, 20))
    reopens = random.choice(REOPEN_DIST)
    rework_minutes = 0
    for r in range(reopens):
        stage = random.choice(["review", "review", "qa"])  # review slightly more common
        theme = random.choice(THEME_WEIGHTS)
        cursor += timedelta(hours=random.randint(3, 30))
        to_status = "Changes Requested" if stage == "review" else "QA Failed"
        ticket_events.append({"id": eid("tk"), "ticket": tid, "event": "reopened",
                              "from_status": "In Review" if stage == "review" else "In QA",
                              "to_status": to_status, "stage": stage,
                              "actor": f"{'reviewer' if stage=='review' else 'qa'}_{random.choice('xyz')}",
                              "ts": iso(cursor)})
        body = random.choice(THEMES[theme])
        review_comments.append({
            "id": eid("rc"), "ticket": tid,
            "source": "github" if stage == "review" else "jira",
            "pr": (f"#{1200 + i}" if stage == "review" else None),
            "reviewer": f"{'reviewer' if stage=='review' else 'qa'}_{random.choice('xyz')}",
            "state": "CHANGES_REQUESTED" if stage == "review" else "QA_FAILED",
            "theme": theme, "body": body, "ts": iso(cursor + timedelta(minutes=2)),
        })
        rework_minutes += random.randint(40, 120)
    cursor += timedelta(hours=random.randint(2, 12))
    ticket_events.append({"id": eid("tk"), "ticket": tid, "event": "closed",
                          "to_status": "Done", "actor": author, "ts": iso(cursor)})
    ground[tid] = {"reopens": reopens, "rework_minutes": rework_minutes}

ticket_events.sort(key=lambda e: e["ts"])
review_comments.sort(key=lambda e: e["ts"])

# --- Ground truth (evaluation only — agents must NOT read this) ---
theme_counts = {}
for rc in review_comments:
    theme_counts[rc["theme"]] = theme_counts.get(rc["theme"], 0) + 1
ground_truth = {
    "workflows": [
        {"name": "Weekly Engineering Report", "actor": "emp_ally", "cadence": "weekly",
         "tools": ["gmail", "jira", "sheets", "slack"], "runs": WEEKS,
         "minutes_per_run": 52, "annual_hours_est": round(52 * 52 / 60, 1)},
        {"name": "Customer CSV Cleanup", "actor": "emp_ben", "cadence": "~4x/week",
         "tools": ["gmail", "sheets", "slack"], "minutes_per_run": 31,
         "annual_hours_est": round(31 * 4 * 52 / 60, 1)},
    ],
    "rework": {
        "tickets": NUM_TICKETS,
        "total_reopens": sum(g["reopens"] for g in ground.values()),
        "rework_hours": round(sum(g["rework_minutes"] for g in ground.values()) / 60, 1),
        "top_themes": sorted(theme_counts.items(), key=lambda x: -x[1]),
    },
}

def dump(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=2)

dump("activity_events.json", activity)
dump("ticket_events.json", ticket_events)
dump("review_comments.json", review_comments)
dump("ground_truth.json", ground_truth)

print(f"activity_events   : {len(activity)}")
print(f"ticket_events     : {len(ticket_events)}")
print(f"review_comments   : {len(review_comments)}")
print(f"tickets           : {NUM_TICKETS}  reopens: {ground_truth['rework']['total_reopens']}  "
      f"rework_hrs: {ground_truth['rework']['rework_hours']}")
print(f"top rework themes : {ground_truth['rework']['top_themes'][:3]}")
print(f"-> wrote 4 files to {OUT}")
