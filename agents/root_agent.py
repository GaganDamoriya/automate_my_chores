"""Root orchestration.

`discovery_pipeline` is the automation lane, run as a deterministic ADK
SequentialAgent: Observer -> Pattern -> Analyst -> Automation -> Verification.
State flows between stages via each agent's output_key (shared session state).

`rework_agent` is a separate lane (see rework.py) triggered on its own schedule.
ADK entrypoint: `root_agent`.
"""
from google.adk.agents import SequentialAgent
from .observer import observer_agent
from .pattern import pattern_agent
from .analyst import analyst_agent
from .automation import automation_agent
from .verification import verification_agent
from .rework import rework_agent

discovery_pipeline = SequentialAgent(
    name="invisible_work_detector",
    description="Observe -> discover -> understand -> automate -> verify.",
    sub_agents=[
        observer_agent,
        pattern_agent,
        analyst_agent,
        automation_agent,
        verification_agent,
    ],
)

# ADK looks for `root_agent` as the module entrypoint.
root_agent = discovery_pipeline
