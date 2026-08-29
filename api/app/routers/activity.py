import asyncio, json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..config import get_settings
from .. import service

try:
    from agents import runtime
except Exception:  # agents package import issue -> tools-only mode
    runtime = None

router = APIRouter(prefix="/activity", tags=["activity"])

def _sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"

@router.get("/stream")
async def stream():
    """Live agent activity feed (SSE).

    Streams REAL ADK events when USE_ADK=1 and a Gemini key is set; otherwise a
    scripted narration so the dashboard still demos without a key.
    """
    settings = get_settings()
    use_real = settings.use_adk and runtime is not None and runtime.adk_available()

    async def gen():
        if use_real:
            try:
                async for line in runtime.stream_events():
                    yield _sse(line)
                return
            except Exception as e:  # fall back mid-stream on any ADK/model error
                yield _sse({"agent": "error", "text": f"ADK run failed ({e}); using fallback."})
        for agent, text in service.AGENT_STEPS:
            yield _sse({"agent": agent, "text": text})
            await asyncio.sleep(0.9)
        yield _sse({"agent": "done", "text": "Discovery complete."})

    return StreamingResponse(gen(), media_type="text/event-stream")
