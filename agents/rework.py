from google.adk.agents import LlmAgent
from .config import MODEL
from . import prompts
from .tools import cluster_issue_themes, build_rework_report

# Parallel discovery lane: evaluates process/ticket quality (never people).
rework_agent = LlmAgent(
    name="rework_quality",
    model=MODEL,
    description="Discovers repeating rework (reopens/QA fails) and writes a weekly report.",
    instruction=prompts.REWORK,
    tools=[cluster_issue_themes, build_rework_report],
    output_key="rework_report",
)
