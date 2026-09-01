"""Automations API — the reworked core.

An automation is persistent: create it (from a spec or a description), see it in the
list with live status, pause (stop) / resume (restart) it, run it now, and read its
run history — each run records the data it produced and the confirmation it sent.
"""
import asyncio, json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..schemas import AutomationCreate, DescriptionRequest
from .. import engine

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from agents.builder import build_spec

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("")
def list_all():
    """Every automation with its status, cadence, next run, and last run."""
    return {"automations": engine.list_automations()}

@router.post("")
def create(body: AutomationCreate):
    """Create an automation from a full spec (used by the dashboard 'Automate' button)."""
    return engine.create_automation(
        name=body.name, description=body.description, kind=body.kind, spec=body.spec,
        cadence=body.cadence, interval_seconds=body.interval_seconds, status=body.status,
        confirm_channel=body.confirm_channel, confirm_target=body.confirm_target)

@router.post("/from-description")
def create_from_description(body: DescriptionRequest):
    """Build an automation from plain English (the chat/search bar)."""
    spec = build_spec(body.description)
    auto = engine.create_automation(
        name=spec["name"], description=body.description, kind=spec["kind"], spec=spec["spec"],
        cadence=spec["cadence"], interval_seconds=spec.get("interval_seconds"),
        confirm_channel=spec["confirm_channel"], confirm_target=spec.get("confirm_target"))
    return {"automation": auto, "parsed": spec}

@router.get("/{aid}")
def get_one(aid: str):
    a = engine.get_automation(aid)
    if not a:
        raise HTTPException(404, "automation not found")
    a["runs"] = engine.list_runs(aid)
    return a

@router.post("/{aid}/pause")
def pause(aid: str):
    a = engine.pause_automation(aid)
    if not a:
        raise HTTPException(404, "automation not found")
    return a

@router.post("/{aid}/resume")
def resume(aid: str):
    a = engine.resume_automation(aid)
    if not a:
        raise HTTPException(404, "automation not found")
    return a

@router.post("/{aid}/run")
async def run_now(aid: str):
    """Fire the automation right now (blocking work runs off the event loop)."""
    if not engine.get_automation(aid):
        raise HTTPException(404, "automation not found")
    run = await asyncio.to_thread(engine.run_automation, aid, "manual")
    return run

@router.delete("/{aid}")
def delete(aid: str):
    if not engine.get_automation(aid):
        raise HTTPException(404, "automation not found")
    engine.delete_automation(aid)
    return {"deleted": aid}

@router.get("/{aid}/runs")
def runs(aid: str):
    if not engine.get_automation(aid):
        raise HTTPException(404, "automation not found")
    return {"runs": engine.list_runs(aid)}

@router.get("/{aid}/stream")
async def stream(aid: str):
    """Reconnectable SSE: tails the automation's latest run log, then its status."""
    def _sse(obj):
        return f"data: {json.dumps(obj)}\n\n"
    async def gen():
        # Persistent tail: streams the current run's log, then keeps watching so the
        # NEXT scheduled run streams live on the same connection (client closes it).
        sent_run, sent = None, 0
        while True:
            latest = engine._latest_run(aid)
            if not latest:
                yield _sse({"_status": "idle"})
                await asyncio.sleep(1.0)
                continue
            if latest["id"] != sent_run:
                sent_run, sent = latest["id"], 0  # a new run appeared — restart the feed
                yield _sse({"_run_start": latest["id"]})
            log = latest["log"]
            while sent < len(log):
                yield _sse(log[sent]); sent += 1
            yield _sse({"_status": latest["status"], "run_id": latest["id"]})
            await asyncio.sleep(0.8)
    return StreamingResponse(gen(), media_type="text/event-stream")
