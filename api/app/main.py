from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import discovery, rework, activity, runs
from . import runengine, pubsub

settings = get_settings()
app = FastAPI(title="Invisible Work Detector API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(discovery.router)
app.include_router(rework.router)
app.include_router(activity.router)
app.include_router(runs.runs_router)
app.include_router(runs.events_router)

@app.on_event("startup")
async def _startup():
    runengine.init_db()
    pubsub.bus.subscribe(pubsub.TOPIC_ACTIVITY, runs.on_activity_detected)

@app.get("/health")
def health():
    return {"ok": True, "model": settings.gemini_model, "use_adk": settings.use_adk}
