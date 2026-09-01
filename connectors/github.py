"""GitHub connector — live PR reviews when connected + GITHUB_REPO set, else seed."""
import os
from .base import load, oauth_token, get_json

def pr_reviews(ticket: str = None) -> list:
    token = oauth_token("github")
    repo = os.environ.get("GITHUB_REPO", "").strip()  # e.g. "owner/name"
    if token and repo:
        status, prs = get_json(f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=20",
                               token=token)
        if isinstance(prs, list):
            out = []
            for pr in prs:
                _, reviews = get_json(
                    f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews", token=token)
                for rv in (reviews if isinstance(reviews, list) else []):
                    if rv.get("state") in ("CHANGES_REQUESTED", "COMMENTED") and rv.get("body"):
                        out.append({"source": "github", "state": rv["state"],
                                    "ticket": pr.get("title", f"PR-{pr['number']}"),
                                    "body": rv["body"]})
            if out:
                return out
    # seed fallback
    rc = [c for c in load("review_comments.json") if c["source"] == "github"]
    return [c for c in rc if (ticket is None or c["ticket"] == ticket)]
