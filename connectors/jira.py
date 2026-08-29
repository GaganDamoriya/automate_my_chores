"""Mock Jira connector."""
from .base import load

def query_done_tickets(jql: str = "status=Done AND sprint=current") -> dict:
    events = load("ticket_events.json")
    done = [e for e in events if e.get("to_status") == "Done"]
    return {"jql": jql, "done_count": len(done), "tickets": [e["ticket"] for e in done][:20]}

def ticket_history(ticket: str) -> list:
    return [e for e in load("ticket_events.json") if e["ticket"] == ticket]
