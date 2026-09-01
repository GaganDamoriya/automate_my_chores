"""Root orchestration for the automation platform.

Two ways the agents run:
  • `discovery_pipeline` — the WATCHER chain (Observer -> Pattern -> Analyst -> Automation
    -> Verification), a deterministic ADK SequentialAgent that observes workflows and
    surfaces automation opportunities. State flows via each agent's output_key.
  • `master_agent` — the chat orchestrator that routes a user message to build an
    automation (via `builder_agent`), suggest opportunities, or answer a question.

ADK looks for `root_agent` as the module entrypoint; we keep the watcher chain there so
`python -m agents.run_local` still streams the full discovery reasoning.
"""
from google.adk.agents import SequentialAgent
from .observer import observer_agent
from .pattern import pattern_agent
from .analyst import analyst_agent
from .automation import automation_agent
from .verification import verification_agent
from .rework import rework_agent
from .builder import builder_agent
from .master import master_agent

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

# ADK entrypoint.
root_agent = discovery_pipeline
