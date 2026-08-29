"""Mock GitHub connector."""
from .base import load

def pr_reviews(ticket: str = None) -> list:
    rc = [c for c in load("review_comments.json") if c["source"] == "github"]
    return [c for c in rc if (ticket is None or c["ticket"] == ticket)]
