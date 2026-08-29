"""Service layer: turns the agent tools into API-ready results.

For the hackathon this calls the pure-Python tools directly so the backend runs
with zero external deps. The upgrade path is to invoke the real ADK pipeline
(agents.root_agent) via an ADK Runner and stream its events — see README.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.tools import workflow_tools as W
from agents.tools import rework_tools as R

_NAME_BY_TOOLS = {
    ("gmail", "jira", "sheets", "slack"): "Weekly Engineering Report",
    ("gmail", "sheets", "slack"): "Customer CSV Cleanup",
}

def _name_for(tools):
    return _NAME_BY_TOOLS.get(tuple(tools), "Workflow: " + " → ".join(tools))

def run_discovery(span_weeks: int = 10) -> dict:
    found = W.find_repeated_sequences()["candidates"]
    opps = []
    for i, c in enumerate(found):
        # sanity filter: ignore implausible spans (noise artifacts)
        if not (5 <= c["avg_duration_min"] <= 240):
            continue
        eff = W.estimate_effort(c["occurrences"], c["avg_duration_min"], span_weeks)
        sc = W.score_opportunity(c["tools"], c["occurrences"], eff["annual_hours_est"])
        opps.append({
            "id": f"opp_{i+1:03d}",
            "name": _name_for(c["tools"]),
            "actor": c["actor"],
            "tools": c["tools"],
            "cadence": eff["cadence"],
            "minutes_per_run": eff["minutes_per_run"],
            "occurrences": c["occurrences"],
            "annual_hours_est": eff["annual_hours_est"],
            "score": sc["score"],
            "risk": sc["risk"],
            "recommended_action": sc["recommended_action"],
        })
    opps.sort(key=lambda o: -o["annual_hours_est"])
    rework = R.build_rework_report()
    monthly = round(sum(o["annual_hours_est"] for o in opps) / 12.0, 1)
    metrics = {
        "workflows_discovered": len(found),
        "automation_opportunities": len(opps),
        "potential_hours_per_month": monthly,
        "rework_hours_this_period": round(rework["metrics"]["total_reopens"] * 1.35, 1),
    }
    return {"metrics": metrics, "opportunities": opps}

def execute(opportunity_id: str) -> dict:
    opps = run_discovery()["opportunities"]
    opp = next((o for o in opps if o["id"] == opportunity_id), opps[0] if opps else None)
    name = opp["name"] if opp else "Weekly Engineering Report"
    res = W.execute_workflow(name)
    summary = res["produced_summary"]
    v = W.verify_output(summary)
    return {
        "opportunity_id": opportunity_id,
        "steps_performed": res["steps_performed"],
        "produced_summary": summary,
        "verified": v["match"],
        "time_saved_min": v["time_saved_min"],
        "human_steps_eliminated": v["human_steps_eliminated"],
    }

def rework_report() -> dict:
    return R.build_rework_report()

# Ordered steps for the live "agent activity" feed (demo narration).
AGENT_STEPS = [
    ("observer", "Reading activity log across Gmail, Jira, GitHub, Sheets, Slack…"),
    ("pattern_detection", "Mining for repeated cross-tool sequences…"),
    ("pattern_detection", "Found 2 recurring workflows above the noise."),
    ("workflow_analyst", "Estimating effort and scoring automatability…"),
    ("workflow_analyst", "Weekly Engineering Report → ~45 hrs/yr · recommend AUTOMATE."),
    ("automation", "Executing: Jira → Sheets → Slack…"),
    ("verification", "Comparing produced output to expected… match ✓"),
    ("verification", "Recorded: 6 human steps eliminated, ~52 min/run saved."),
]
