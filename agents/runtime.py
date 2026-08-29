"""ADK runtime harness.

Runs the real ADK pipeline (Gemini) via a Runner and streams its events, so the
dashboard's live feed shows the agents actually reasoning. Import-guarded: if
google-adk isn't installed the module still imports, and `adk_available()` returns
False so callers fall back to the deterministic tool path.

Requires: `pip install google-adk` and GEMINI_API_KEY (AI Studio) or Vertex config.
"""
import os

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from .root_agent import discovery_pipeline
    from .rework import rework_agent
    _ADK_IMPORTED = True
except Exception:  # google-adk not installed
    _ADK_IMPORTED = False
    discovery_pipeline = rework_agent = None

APP_NAME = "invisible_work_detector"
_DISCOVERY_PROMPT = (
    "Discover invisible work in the connected activity log: find the repeated "
    "workflows, estimate their annual cost, decide what to automate, then run and "
    "verify the top one."
)


def adk_available() -> bool:
    """True if google-adk is importable AND creds are configured.

    Vertex mode: needs GOOGLE_GENAI_USE_VERTEXAI=TRUE + GOOGLE_CLOUD_PROJECT (auth
    via Application Default Credentials). AI Studio mode: needs an API key.
    """
    if not _ADK_IMPORTED:
        return False
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() in ("TRUE", "1"):
        return bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
    return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))


def _event_line(event):
    """Render one ADK event as a short human line for the live feed."""
    try:
        calls = event.get_function_calls()
        if calls:
            return "→ calling " + ", ".join(c.name for c in calls)
    except Exception:
        pass
    try:
        resps = event.get_function_responses()
        if resps:
            return "✓ results from " + ", ".join(r.name for r in resps)
    except Exception:
        pass
    content = getattr(event, "content", None)
    if content and getattr(content, "parts", None):
        txt = "".join(getattr(p, "text", "") or "" for p in content.parts)
        if txt.strip():
            return txt.strip()[:300]
    return None


async def _new_runner(agent):
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id="demo")
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
    return runner, session, session_service


async def stream_events(agent=None, prompt: str = _DISCOVERY_PROMPT):
    """Async-generate {agent, text} dicts from a live ADK run (for SSE)."""
    agent = agent or discovery_pipeline
    runner, session, _ = await _new_runner(agent)
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(user_id="demo", session_id=session.id, new_message=content):
        line = _event_line(event)
        if line:
            yield {"agent": getattr(event, "author", None) or "agent", "text": line}
    yield {"agent": "done", "text": "Discovery complete."}


async def run_and_get_state(agent=None, prompt: str = _DISCOVERY_PROMPT):
    """Run the pipeline to completion; return the final text + session state."""
    agent = agent or discovery_pipeline
    runner, session, session_service = await _new_runner(agent)
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    final = ""
    async for event in runner.run_async(user_id="demo", session_id=session.id, new_message=content):
        is_final = getattr(event, "is_final_response", None)
        if is_final and event.is_final_response() and getattr(event, "content", None):
            final = "".join(getattr(p, "text", "") or "" for p in event.content.parts)
    got = await session_service.get_session(app_name=APP_NAME, user_id="demo", session_id=session.id)
    return {"final": final, "state": dict(got.state) if got else {}}
