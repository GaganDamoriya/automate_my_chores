from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import verify_output

verification_agent = LlmAgent(
    name="verification",
    model=MODEL,
    description="Checks the automation's output against the expected result and records savings.",
    instruction=prompts.VERIFICATION,
    tools=[verify_output],
    output_key="verification",
)
