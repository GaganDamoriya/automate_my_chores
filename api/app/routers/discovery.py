from fastapi import APIRouter
from ..schemas import DiscoveryResult, ExecutionResult
from ..config import get_settings
from .. import service

try:
    from agents import runtime
except Exception:
    runtime = None

router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.get("/run", response_model=DiscoveryResult)
def run():
    """Run the discovery lane and return metrics + scored opportunities (tool logic)."""
    return service.run_discovery()

@router.post("/execute/{opportunity_id}", response_model=ExecutionResult)
def execute(opportunity_id: str):
    """Approve + execute one opportunity, then verify the result."""
    return service.execute(opportunity_id)

@router.post("/analyze")
async def analyze():
    """Run the REAL ADK pipeline (Gemini) and return its reasoning + session state.

    Requires USE_ADK=1 and a Gemini key; otherwise returns a hint and the tool result.
    """
    settings = get_settings()
    if not (settings.use_adk and runtime is not None and runtime.adk_available()):
        return {"mode": "tools",
                "note": "Set USE_ADK=1 and GEMINI_API_KEY (and pip install google-adk) to run the real agents.",
                "tool_result": service.run_discovery()}
    result = await runtime.run_and_get_state()
    return {"mode": "adk", **result}
