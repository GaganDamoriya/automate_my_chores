from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import find_repeated_sequences

pattern_agent = LlmAgent(
    name="pattern_detection",
    model=MODEL,
    description="Finds repeated cross-tool sequences (candidate workflows).",
    instruction=prompts.PATTERN,
    tools=[find_repeated_sequences],
    output_key="candidate_workflows",
)
