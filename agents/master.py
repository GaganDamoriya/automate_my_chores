"""Master orchestrator — routes a chat message to an intent.

`route()` is the pure-Python intent classifier the API's /chat endpoint uses (works
with zero deps). `master_agent` is the ADK/LLM version for the real-agent path.
Intents: 'build' (create an automation), 'suggest' (discover opportunities),
'ask' (general question).
"""
import re

_BUILD_HINTS = [
    "automate", "create", "set up", "setup", "build", "make an automation",
    "schedule", "every day", "every morning", "every week", "each ", "daily",
    "weekly", "hourly", "every ", "post to", "send me", "remind", "watch for",
    "clean up", "summarize", "digest",
]
_SUGGEST_HINTS = [
    "what can i automate", "what should i automate", "suggest", "suggestion",
    "find invisible work", "invisible work", "opportunit", "what's repetitive",
    "what is repetitive", "where am i wasting", "discover",
]

def route(message: str) -> str:
    t = (message or "").lower().strip()
    if any(h in t for h in _SUGGEST_HINTS):
        return "suggest"
    # A cadence or an imperative verb over a tool reads as "build me an automation".
    if any(h in t for h in _BUILD_HINTS):
        return "build"
    if re.search(r"\b(how|what|why|when|status|show|list|explain)\b", t):
        return "ask"
    return "build" if len(t.split()) >= 4 else "ask"


# --- Real-LLM version (ADK). Import-guarded.
try:
    from google.adk.agents import LlmAgent
    from .config import MODEL
    from . import prompts
    from .builder import propose_spec

    master_agent = LlmAgent(
        name="master",
        model=MODEL,
        description="Routes a user's chat message to build / suggest / ask and orchestrates the response.",
        instruction=prompts.MASTER,
        tools=[propose_spec],
        output_key="master_reply",
    )
except Exception:  # google-adk not installed
    master_agent = None
