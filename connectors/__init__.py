"""Mock tool connectors.

For the hackathon these read seeded data and write to an in-memory sink, so the
autonomous loop runs end to end with zero live-API risk. Each mirrors the shape of
the real API call it stands in for; swap the body for a real client behind a flag.
"""
from . import gmail, jira, github, sheets, slack  # noqa: F401
