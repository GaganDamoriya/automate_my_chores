"""Chat / search-bar endpoint — the dashboard's primary control.

Routes a plain-English message to an intent and acts on it: BUILD an automation,
SUGGEST opportunities from discovery, or ASK (answer about the current state).
Pure-Python routing so it works without Gemini; the ADK master_agent is the
real-LLM upgrade path.
"""
import sys, os
from fastapi import APIRouter
from ..schemas import ChatRequest
from .. import engine, service

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from agents.master import route
from agents.builder import build_spec

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def chat(body: ChatRequest):
    msg = body.message or ""
    intent = route(msg)

    if intent == "build":
        spec = build_spec(msg)
        auto = engine.create_automation(
            name=spec["name"], description=msg, kind=spec["kind"], spec=spec["spec"],
            cadence=spec["cadence"], interval_seconds=spec.get("interval_seconds"),
            confirm_channel=spec["confirm_channel"], confirm_target=spec.get("confirm_target"))
        cad = auto["cadence"] if not auto["interval_seconds"] else f"every {auto['interval_seconds']}s"
        ch = auto["confirm_channel"] + (f" ({auto['confirm_target']})" if auto["confirm_target"] else "")
        reply = (f"Created **{auto['name']}** — runs {cad}, confirms via {ch}. "
                 f"It's active now; you can stop or restart it on the Automations page.")
        return {"intent": intent, "reply": reply, "created_automation": auto, "parsed": spec}

    if intent == "suggest":
        disc = service.run_discovery()
        opps = disc["opportunities"]
        if opps:
            top = opps[0]
            reply = (f"I found {len(opps)} automation opportunities. Top one: **{top['name']}** "
                     f"(~{top['annual_hours_est']} hrs/yr, {top['tools']}). "
                     f"Hit Automate on a card below to spin it up.")
        else:
            reply = "No clear repeated workflows surfaced yet."
        return {"intent": intent, "reply": reply, "suggestions": opps, "metrics": disc["metrics"]}

    # ask
    autos = engine.list_automations()
    active = sum(1 for a in autos if a["status"] == "active")
    reply = (f"You have {len(autos)} automations ({active} active). Ask me to automate something "
             f"— e.g. \"every morning post a Jira digest to #standup\" — or say \"what can I automate?\" "
             f"to see opportunities.")
    return {"intent": "ask", "reply": reply, "automations": autos}
