from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import estimate_effort, score_opportunity

analyst_agent = LlmAgent(
    name="workflow_analyst",
    model=MODEL,
    description="Decides whether a workflow is worth automating, eliminating, or investigating.",
    instruction=prompts.ANALYST,
    tools=[estimate_effort, score_opportunity],
    output_key="opportunities",
)
