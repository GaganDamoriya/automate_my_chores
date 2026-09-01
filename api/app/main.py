from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import discovery, rework, activity, automations, chat, auth
from . import engine, credentials

settings = get_settings()
app = FastAPI(title="Invisible Work Automation Platform API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(automations.router)   # the reworked core
app.include_router(chat.router)          # dashboard chat / search bar
app.include_router(discovery.router)     # invisible-work suggestions
app.include_router(rework.router)        # rework report data (surfaced via an automation)
app.include_router(activity.router)      # live agent feed (SSE)
app.include_router(auth.router)          # OAuth connect/disconnect

@app.on_event("startup")
async def _startup():
    engine.init_db()
    credentials.init_db()
    engine.seed_defaults()      # populate default automations on first boot
    engine.start_scheduler()    # fire active automations on their cadence

@app.get("/health")
def health():
    return {"ok": True, "model": settings.gemini_model, "use_adk": settings.use_adk}
