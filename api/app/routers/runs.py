import asyncio, json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .. import runengine, pubsub

runs_router = APIRouter(prefix="/runs", tags=["runs"])
events_router = APIRouter(prefix="/events", tags=["events"])

_TASKS = set()  # keep background task refs alive

def _spawn(coro):
    t = asyncio.create_task(coro)
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)
    return t

def _sse(obj):
    return f"data: {json.dumps(obj)}\n\n"


@runs_router.post("")
def start_run():
    """Start a discovery run in the background. Returns immediately; the run
    keeps advancing server-side even if the client disconnects."""
    run_id = runengine.create_run("manual")
    _spawn(runengine.advance_to_gate(run_id))
    return runengine.get_run(run_id)

@runs_router.get("")
def list_runs():
    return runengine.list_runs()

@runs_router.get("/{run_id}")
def get_run(run_id: str):
    """Durable run state — call this after reconnecting to see where it got to."""
    run = runengine.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run

@runs_router.post("/{run_id}/approve")
def approve(run_id: str):
    """Approve the gate; the run resumes (execute → verify) in the background."""
    if not runengine.approve(run_id):
        raise HTTPException(409, "run is not awaiting approval")
    _spawn(runengine.execute_after_gate(run_id))
    return runengine.get_run(run_id)

@runs_router.get("/{run_id}/stream")
async def stream(run_id: str):
    """Reconnectable SSE: replays the full durable log on connect, then tails it.
    Closing and reopening the tab resumes exactly where the run is."""
    async def gen():
        sent = 0
        while True:
            run = runengine.get_run(run_id)
            if not run:
                yield _sse({"error": "not found"}); return
            log = run["log"]
            while sent < len(log):
                yield _sse(log[sent]); sent += 1
            yield _sse({"_status": run["status"], "opportunity": run.get("opportunity_name"),
                        "approved": run["approved"]})
            if run["status"] in ("done", "failed"):
                return
            await asyncio.sleep(0.7)
    return StreamingResponse(gen(), media_type="text/event-stream")


async def on_activity_detected(data):
    """Pub/Sub handler: a new-activity event wakes the agent and starts a run."""
    run_id = runengine.create_run("pubsub:" + str(data.get("source", "activity")))
    _spawn(runengine.advance_to_gate(run_id))
    return run_id

@events_router.post("/ingest")
async def ingest(payload: dict | None = None):
    """Simulate a Pub/Sub message ('new activity detected') that triggers a run."""
    run_id = await pubsub.bus.publish(pubsub.TOPIC_ACTIVITY, payload or {"source": "gmail"})
    return {"triggered": True, "run_id": run_id}
