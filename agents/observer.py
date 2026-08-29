from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import load_activity_events

observer_agent = LlmAgent(
    name="observer",
    model=MODEL,
    description="Understands what work is actually happening across connected tools.",
    instruction=prompts.OBSERVER,
    tools=[load_activity_events],
    output_key="observation",
)
