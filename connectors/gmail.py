"""Gmail connector — live send via the Gmail API when connected; download is seeded."""
import base64
from email.mime.text import MIMEText
from .base import oauth_token, post_json

def download_attachment(query: str = "eng_report.csv") -> dict:
    return {"file": query, "rows": 128, "source": "seed"}

def send_message(to: str, subject: str, body: str, sender: str = "me") -> dict:
    """Send an email via the Gmail API. Returns a record with source/sent flags.
    Falls back (sent=False) if not connected — the caller decides what to do next."""
    token = oauth_token("google")
    if not token:
        return {"to": to, "subject": subject, "sent": False, "source": "seed",
                "detail": "Google not connected."}
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    status, resp = post_json("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                             {"raw": raw}, token=token)
    ok = bool(resp.get("id"))
    return {"to": to, "subject": subject, "sent": ok, "source": "live",
            "id": resp.get("id"), "detail": "" if ok else resp.get("error", "gmail_error")}
