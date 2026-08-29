"""Rework & Quality lane tools (ADK function tools).

Evaluate PROCESS and TICKET quality, not people. All aggregation is by issue theme
and ticket — never by individual. Real logic, runnable without Gemini.
"""
import json, os, re
from collections import defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.environ.get("SEED_DIR", os.path.join(_REPO, "seed", "data"))

def _load(name):
    with open(os.path.join(_DATA, name)) as f:
        return json.load(f)

# Keyword rules to cluster free-text review/QA comments into root-cause themes.
_THEME_RULES = {
    "missing_tests": ["test", "coverage", "regression", "edge case", "empty"],
    "spec_misunderstanding": ["ticket asked", "acceptance criteria", "requirement", "spec", "not what"],
    "null_handling": ["null", "nullpointer", "npe", "missing"],
    "error_handling": ["exception", "retry", "backoff", "5xx", "swallow"],
    "flaky_test": ["flaky", "intermittent", "timing", "sleep"],
    "style": ["naming", "readability", "nit", "helper", "extract"],
}

def _classify(text: str) -> str:
    t = text.lower()
    for theme, kws in _THEME_RULES.items():
        if any(k in t for k in kws):
            return theme
    return "other"


def cluster_issue_themes() -> dict:
    """Cluster reopen/QA/review comments into recurring root-cause themes.

    Reads review_comments.json, classifies each comment by its text, and ranks the
    themes by frequency. Attaches a representative quote per theme.

    Returns:
        dict with ranked themes: {theme, count, stages, example_quote}.
    """
    comments = _load("review_comments.json")
    buckets = defaultdict(list)
    for c in comments:
        buckets[_classify(c["body"])].append(c)
    themes = []
    for theme, items in buckets.items():
        stages = sorted({("review" if i["state"] == "CHANGES_REQUESTED" else "qa") for i in items})
        themes.append({
            "theme": theme,
            "count": len(items),
            "stages": stages,
            "example_quote": items[0]["body"],
            "tickets": sorted({i["ticket"] for i in items}),
        })
    themes.sort(key=lambda x: -x["count"])
    return {"total_comments": len(comments), "themes": themes}


def build_rework_report(week_of: str = "2026-08-24") -> dict:
    """Assemble the weekly rework report from ticket + comment signals.

    Args:
        week_of: label for the reporting week.
    Returns:
        dict: metrics, repeating issues, most-reopened tickets, and a recommendation.
    """
    ticket_events = _load("ticket_events.json")
    reopen_by_ticket = defaultdict(int)
    title_by_ticket = {}
    stage_by_ticket = defaultdict(list)
    for e in ticket_events:
        if e.get("title"):
            title_by_ticket[e["ticket"]] = e["title"]
        if e["event"] == "reopened":
            reopen_by_ticket[e["ticket"]] += 1
            stage_by_ticket[e["ticket"]].append(e.get("stage", "?"))

    total_reopens = sum(reopen_by_ticket.values())
    tickets_reopened = len(reopen_by_ticket)
    themes = cluster_issue_themes()["themes"]
    top = themes[0] if themes else None

    most_reopened = sorted(reopen_by_ticket.items(), key=lambda x: -x[1])[:5]
    most_reopened = [{
        "ticket": t, "title": title_by_ticket.get(t, ""),
        "reopens": n, "stages": stage_by_ticket[t],
    } for t, n in most_reopened]

    recommendation = None
    if top and top["theme"] == "missing_tests":
        recommendation = ("Most reopens trace to missing edge-case tests, mostly at QA. "
                          "Recommend a PR test-coverage gate on the repos where it clusters.")
    elif top:
        recommendation = f"Top repeating issue is '{top['theme']}'. Look into it: {top['example_quote']}"

    return {
        "week_of": week_of,
        "metrics": {
            "tickets_reopened": tickets_reopened,
            "total_reopens": total_reopens,
            "avg_reopens_per_ticket": round(total_reopens / max(tickets_reopened, 1), 1),
        },
        "repeating_issues": themes[:4],
        "most_reopened_tickets": most_reopened,
        "what_to_look_into": recommendation,
    }
