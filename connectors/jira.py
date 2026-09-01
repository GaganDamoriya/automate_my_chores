"""Jira connector — live Atlassian REST when connected, else seed."""
from .base import load, oauth_token, jira_cloudid, get_json

def query_done_tickets(jql: str = "status=Done AND sprint in openSprints()") -> dict:
    token = oauth_token("jira")
    cloudid = jira_cloudid()
    if token and cloudid:
        from urllib.parse import quote
        url = (f"https://api.atlassian.com/ex/jira/{cloudid}/rest/api/3/search"
               f"?jql={quote(jql)}&maxResults=20&fields=key")
        status, resp = get_json(url, token=token)
        issues = resp.get("issues")
        if issues is not None:
            keys = [i.get("key") for i in issues]
            return {"jql": jql, "done_count": len(keys), "tickets": keys, "source": "live"}
    # seed fallback
    events = load("ticket_events.json")
    done = [e for e in events if e.get("to_status") == "Done"]
    return {"jql": jql, "done_count": len(done),
            "tickets": [e["ticket"] for e in done][:20], "source": "seed"}

def ticket_history(ticket: str) -> list:
    return [e for e in load("ticket_events.json") if e["ticket"] == ticket]
