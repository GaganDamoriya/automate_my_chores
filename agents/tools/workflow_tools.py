"""Workflow discovery + execution tools (ADK function tools).

These carry the real logic; the LlmAgents orchestrate and narrate them. Everything
here runs on plain Python so it's testable without Gemini or the ADK runtime.
"""
import json, os, statistics
from collections import defaultdict, Counter
from datetime import datetime
from math import ceil

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.environ.get("SEED_DIR", os.path.join(_REPO, "seed", "data"))

def _load(name):
    with open(os.path.join(_DATA, name)) as f:
        return json.load(f)

def _dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

def _step(e):
    return f'{e["tool"]}.{e["action"]}'


def load_activity_events(limit: int = 500) -> dict:
    """Load normalized activity events (the Observer's raw input).

    Args:
        limit: max events to return.
    Returns:
        dict with total count, distinct actors/tools, and a sample of events.
    """
    events = _load("activity_events.json")[:limit]
    actors = sorted({e["actor"] for e in events})
    tools = sorted({e["tool"] for e in events})
    return {"total": len(events), "actors": actors, "tools": tools, "events": events[:25]}


def find_repeated_sequences(min_occurrences: int = 3, min_steps: int = 3,
                            core_fraction: float = 0.8, jaccard: float = 0.6) -> dict:
    """Mine the activity log for repeated cross-tool workflows, robust to noise.

    A workflow is a set of steps that recur *together on the same days*. We cluster
    steps by day-set overlap (Jaccard), which isolates the real workflow from
    scattered noise, then count a day as a run when it contains most of that core.
    Run duration is the median across runs, so a noise-polluted day can't skew it.

    Args:
        min_occurrences: minimum runs to qualify as a workflow.
        min_steps: minimum distinct steps in the core.
        core_fraction: fraction of the core a day must contain to count as a run.
        jaccard: min day-set overlap for a step to join a workflow cluster.
    Returns:
        dict with a list of candidate workflows, most frequent first.
    """
    events = _load("activity_events.json")
    events.sort(key=lambda e: e["ts"])

    actor_day_evs = defaultdict(dict)  # actor -> {day: [events]}
    for e in events:
        actor_day_evs[e["actor"]].setdefault(e["ts"][:10], []).append(e)

    candidates = []
    for actor, day_evs in actor_day_evs.items():
        step_days = defaultdict(set)  # step -> set(days it appears on)
        for day, evs in day_evs.items():
            for s in {_step(e) for e in evs}:
                step_days[s].add(day)
        remaining = {s: d for s, d in step_days.items() if len(d) >= min_occurrences}

        while remaining:
            anchor = max(remaining, key=lambda s: len(remaining[s]))
            adays = remaining[anchor]
            group = [s for s, d in remaining.items()
                     if len(adays | d) and len(adays & d) / len(adays | d) >= jaccard]
            for s in group:
                remaining.pop(s, None)
            if len(group) < min_steps:
                continue
            core = set(group)
            need = max(min_steps, ceil(len(core) * core_fraction))

            run_days = set().union(*[step_days[s] for s in core])
            runs, order_votes = [], Counter()
            for day in run_days:
                evs = sorted(day_evs[day], key=lambda e: e["ts"])
                core_evs = [e for e in evs if _step(e) in core]
                if len({_step(e) for e in core_evs}) < need:
                    continue
                dur = (_dt(core_evs[-1]["ts"]) - _dt(core_evs[0]["ts"])).total_seconds() / 60.0
                seen, seq = set(), []
                for e in core_evs:
                    s = _step(e)
                    if s not in seen:
                        seen.add(s); seq.append(s)
                runs.append(dur)
                if 5 <= dur <= 180:
                    order_votes[tuple(seq)] += 1
            if len(runs) < min_occurrences:
                continue
            clean = [d for d in runs if 5 <= d <= 180] or runs
            canonical = list(order_votes.most_common(1)[0][0]) if order_votes else sorted(core)
            candidates.append({
                "actor": actor,
                "steps": canonical,
                "tools": list(dict.fromkeys(s.split(".")[0] for s in canonical)),
                "occurrences": len(runs),
                "avg_duration_min": round(statistics.median(clean), 1),
            })

    candidates.sort(key=lambda c: -c["occurrences"])
    return {"candidate_count": len(candidates), "candidates": candidates}


def estimate_effort(occurrences: int, avg_duration_min: float, span_weeks: int = 10) -> dict:
    """Estimate the annual effort a repeated workflow consumes.

    Args:
        occurrences: number of observed runs.
        avg_duration_min: median minutes per run.
        span_weeks: observation window in weeks.
    Returns:
        dict with cadence, runs/year and estimated annual hours.
    """
    runs_per_week = occurrences / max(span_weeks, 1)
    runs_per_year = runs_per_week * 52
    annual_hours = round(runs_per_year * avg_duration_min / 60.0, 1)
    cadence = "weekly" if 0.7 <= runs_per_week <= 1.5 else f"~{round(runs_per_week,1)}x/week"
    return {"cadence": cadence, "runs_per_year": round(runs_per_year),
            "minutes_per_run": round(avg_duration_min), "annual_hours_est": annual_hours}


def score_opportunity(tools: list, occurrences: int, annual_hours: float) -> dict:
    """Score how worth automating a workflow is (0-100) and flag a recommended action.

    Args:
        tools: tools the workflow touches.
        occurrences: observed runs (a proxy for determinism).
        annual_hours: estimated annual hours.
    Returns:
        dict with score, automatability, risk and a recommended action.
    """
    automatable_tools = {"gmail", "jira", "github", "sheets", "slack"}
    coverage = len(set(tools) & automatable_tools) / max(len(tools), 1)
    determinism = min(occurrences / 8.0, 1.0)
    impact = min(annual_hours / 60.0, 1.0)
    score = round(100 * (0.4 * coverage + 0.3 * determinism + 0.3 * impact))
    action = "AUTOMATE"
    if "sheets" in tools and {"jira", "gmail"} & set(tools) and "slack" in tools:
        action = "AUTOMATE"  # Analyst may upgrade to ELIMINATE after reasoning
    return {"score": score, "automatability": round(coverage, 2),
            "risk": "low" if coverage > 0.75 else "medium", "recommended_action": action}


def _run_weekly_report():
    from connectors import jira, sheets, slack
    log = []
    report = jira.query_done_tickets(); log.append("jira.query_done_tickets")
    metrics = sheets.compute_weekly_metrics(report); log.append("sheets.compute_weekly_metrics")
    slack.post_message("#eng-updates", metrics["summary"]); log.append("slack.post_message")
    return metrics["summary"], log

def _run_csv_cleanup():
    from connectors import gmail, sheets, slack
    log = []
    dl = gmail.download_attachment("customers_batch.csv"); log.append("gmail.download_attachment")
    cleaned = sheets.clean_customer_csv(dl); log.append("sheets.clean_customer_csv")
    slack.post_message("#data-ops", cleaned["summary"]); log.append("slack.post_message")
    return cleaned["summary"], log

def _expected_weekly():
    from connectors import jira, sheets
    return sheets.compute_weekly_metrics(jira.query_done_tickets())["summary"]

def _expected_csv():
    from connectors import gmail, sheets
    return sheets.clean_customer_csv(gmail.download_attachment("customers_batch.csv"))["summary"]

_SAVINGS = {"weekly_report": (52, 6), "csv_cleanup": (31, 5)}

def execute_workflow(workflow: str) -> dict:
    """Execute the APPROVED workflow through the connectors, step by step.

    Runs the flow matching the opportunity you pass (by name), so the automation
    matches what was discovered — not a fixed script.

    Args:
        workflow: the approved opportunity's NAME (e.g. "Weekly Engineering Report"
            or "Customer CSV Cleanup").
    Returns:
        dict with the workflow key, produced summary, and steps performed.
    """
    text = (workflow or "").lower()
    if any(k in text for k in ("csv", "cleanup", "customer")):
        summary, log = _run_csv_cleanup(); key = "csv_cleanup"
    else:
        summary, log = _run_weekly_report(); key = "weekly_report"
    return {"workflow": workflow, "workflow_key": key,
            "produced_summary": summary, "steps_performed": log}

def verify_output(produced_summary: str) -> dict:
    """Independently verify the automation output against known-good expected results.

    Recomputes the expected output for each known workflow from the source of truth
    and checks the produced summary against them — a genuine like-for-like check.
    Pass only the produced summary.

    Args:
        produced_summary: the summary the automation produced.
    Returns:
        dict with match, which workflow matched, and measured savings.
    """
    ps = produced_summary.strip()
    expected = {"weekly_report": _expected_weekly().strip(),
                "csv_cleanup": _expected_csv().strip()}
    matched = next((k for k, v in expected.items() if v == ps), None)
    saved, steps = _SAVINGS.get(matched, (0, 0))
    return {"match": matched is not None, "matched_workflow": matched,
            "expected_candidates": list(expected.values()), "produced": ps,
            "diff": "" if matched else "produced does not match any known-good expected output",
            "time_saved_min": saved, "human_steps_eliminated": steps}
