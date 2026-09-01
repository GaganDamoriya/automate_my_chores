from pydantic import BaseModel
from typing import Optional

class Opportunity(BaseModel):
    id: str
    name: str
    actor: str
    tools: list[str]
    cadence: str
    minutes_per_run: int
    occurrences: int
    annual_hours_est: float
    score: int
    risk: str
    recommended_action: str

class Metrics(BaseModel):
    workflows_discovered: int
    automation_opportunities: int
    potential_hours_per_month: float
    rework_hours_this_period: float

class DiscoveryResult(BaseModel):
    metrics: Metrics
    opportunities: list[Opportunity]

class ExecutionResult(BaseModel):
    opportunity_id: str
    steps_performed: list[str]
    produced_summary: str
    verified: bool
    time_saved_min: int
    human_steps_eliminated: int


# --- Automations (reworked core) -------------------------------------------

class AutomationCreate(BaseModel):
    name: str
    description: str = ""
    kind: str = "workflow"           # workflow | rework | custom
    spec: dict = {}
    cadence: str = "every 5 min"
    interval_seconds: Optional[int] = None
    status: str = "active"           # active | paused
    confirm_channel: str = "slack"   # slack | gmail | both | none
    confirm_target: Optional[str] = None

class DescriptionRequest(BaseModel):
    description: str

class ChatRequest(BaseModel):
    message: str
