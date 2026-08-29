from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import execute_workflow

automation_agent = LlmAgent(
    name="automation",
    model=MODEL,
    description="Executes an approved workflow through the connected tools.",
    instruction=prompts.AUTOMATION,
    tools=[execute_workflow],
    output_key="execution_result",
)
