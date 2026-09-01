"""Automation Builder — turns a plain-English description into an automation spec.

This is what powers "type what you want to automate and it builds it". The pure
Python `build_spec()` runs with zero external deps (so the API works without
Gemini); the ADK `builder_agent` is the real-LLM version used on the agent path.

A spec looks like:
    {
      "name": "Morning Jira digest",
      "kind": "workflow" | "rework" | "custom",
      "spec": {"workflow_name": "...", "tools": ["jira","slack"], "steps": [...]},
      "cadence": "daily",
      "interval_seconds": None,
      "confirm_channel": "slack" | "gmail" | "both",
      "confirm_target": "#channel" or "email@x.com",
    }
"""
import re

_TOOL_WORDS = {
    "jira": ["jira", "ticket", "issue", "sprint"],
    "github": ["github", "pr", "pull request", "commit", "review"],
    "gmail": ["gmail", "email", "inbox", "attachment", "mail"],
    "sheets": ["sheet", "spreadsheet", "csv", "excel"],
    "slack": ["slack", "channel", "post", "message", "notify", "ping"],
}

_CADENCE_PATTERNS = [
    (r"every\s+(\d+)\s*sec", lambda m: (None, int(m.group(1)))),
    (r"every\s+(\d+)\s*min", lambda m: (None, int(m.group(1)) * 60)),
    (r"every\s+(\d+)\s*hour", lambda m: (None, int(m.group(1)) * 3600)),
    (r"\bhour(ly)?\b", lambda m: ("hourly", None)),
    (r"(every\s+day|daily|each\s+day|every\s+morning|each\s+morning|morning)", lambda m: ("daily", None)),
    (r"(every\s+week|weekly|each\s+week)", lambda m: ("weekly", None)),
]

def _detect_tools(t):
    found = [tool for tool, words in _TOOL_WORDS.items() if any(w in t for w in words)]
    return found or ["slack"]

def _detect_cadence(t):
    for pat, fn in _CADENCE_PATTERNS:
        m = re.search(pat, t)
        if m:
            return fn(m)
    return ("daily", None)  # sensible default

def _detect_channel(t):
    if any(w in t for w in ["email", "gmail", "mail", "inbox"]) and "slack" in t:
        return "both", None
    if any(w in t for w in ["email", "gmail", "mail", "inbox"]):
        return "gmail", None
    m = re.search(r"#([a-z0-9_-]+)", t)
    return "slack", ("#" + m.group(1) if m else None)

def _name_from(description):
    words = re.sub(r"[^a-zA-Z0-9 ]", " ", description).split()
    name = " ".join(words[:6]).strip().title()
    return name or "Custom Automation"


def _default_target(channel, target, slack_default):
    if target:
        return target
    return slack_default if channel == "slack" else None


def build_spec(description: str) -> dict:
    """Deterministically parse a description into an automation spec (no LLM)."""
    t = (description or "").lower()
    cadence, interval = _detect_cadence(t)
    channel, target = _detect_channel(t)

    # Map to a known, verifiable workflow when the description clearly matches one.
    if any(k in t for k in ["rework", "reopen", "quality", "bounce back", "qa fail", "review fail"]):
        return {"name": "Rework Intelligence", "kind": "rework",
                "spec": {"tools": ["jira", "github"]},
                "cadence": cadence or "weekly", "interval_seconds": interval,
                "confirm_channel": channel, "confirm_target": _default_target(channel, target, "#quality")}
    if any(k in t for k in ["weekly report", "engineering report", "eng report", "sprint report", "standup report"]):
        return {"name": "Weekly Engineering Report", "kind": "workflow",
                "spec": {"workflow_name": "Weekly Engineering Report", "tools": ["jira", "sheets", "slack"]},
                "cadence": cadence or "weekly", "interval_seconds": interval,
                "confirm_channel": channel, "confirm_target": _default_target(channel, target, "#eng-updates")}
    if any(k in t for k in ["csv", "cleanup", "clean up", "dedupe", "customer list", "normalize"]):
        return {"name": "Customer CSV Cleanup", "kind": "workflow",
                "spec": {"workflow_name": "Customer CSV Cleanup", "tools": ["gmail", "sheets", "slack"]},
                "cadence": cadence, "interval_seconds": interval,
                "confirm_channel": channel, "confirm_target": _default_target(channel, target, "#data-ops")}

    # Otherwise: a novel custom automation over the detected tools.
    tools = _detect_tools(t)
    steps = [f"{tool}.run" for tool in tools]
    return {"name": _name_from(description), "kind": "custom",
            "spec": {"tools": tools, "steps": steps, "source_description": description},
            "cadence": cadence, "interval_seconds": interval,
            "confirm_channel": channel, "confirm_target": target}


# --- Real-LLM version (ADK). Import-guarded so the module loads without google-adk.
try:
    from google.adk.agents import LlmAgent
    from .config import MODEL
    from . import prompts

    def propose_spec(description: str) -> dict:
        """ADK function tool: propose a structured automation spec from a description."""
        return build_spec(description)

    builder_agent = LlmAgent(
        name="automation_builder",
        model=MODEL,
        description="Turns a plain-English description into a runnable automation spec.",
        instruction=prompts.BUILDER,
        tools=[propose_spec],
        output_key="automation_spec",
    )
except Exception:  # google-adk not installed
    builder_agent = None
