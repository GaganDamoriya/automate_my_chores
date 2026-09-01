"""Confirmation connector — OAuth-first, then static creds, then simulated. Demo-safe.

Every automation sends a "job done" confirmation. Delivery preference, per channel:
  Slack:  OAuth bot token (chat.postMessage) -> SLACK_WEBHOOK_URL -> simulated
  Gmail:  OAuth (Gmail API send)             -> SMTP app-password -> simulated
If nothing is configured the message is still recorded (simulated=True) so a live demo
never fails on a missing secret. Stdlib only.
"""
import os, json, smtplib, ssl
from email.mime.text import MIMEText
from urllib import request, error
from .base import oauth_token, post_json
from . import gmail as gmail_conn


def _slack(subject: str, body: str, target: str | None):
    text = f"*{subject}*\n{body}"
    channel = target or os.environ.get("SLACK_DEFAULT_CHANNEL", "").strip() or None
    rec = {"channel": "slack", "target": channel, "subject": subject,
           "body": text, "sent": False, "simulated": True, "detail": ""}

    # 1) OAuth bot token (needs a channel to post to)
    token = oauth_token("slack")
    if token and channel:
        status, resp = post_json("https://slack.com/api/chat.postMessage",
                                 {"channel": channel, "text": text}, token=token)
        if resp.get("ok"):
            rec.update(sent=True, simulated=False, detail=f"Posted to {channel} via Slack bot.")
            return rec
        rec["detail"] = f"Slack bot error: {resp.get('error', 'unknown')} — "

    # 2) incoming webhook
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if url:
        try:
            req = request.Request(url, data=json.dumps({"text": text}).encode(),
                                  headers={"Content-Type": "application/json"})
            with request.urlopen(req, timeout=10) as resp:
                ok = resp.status == 200
            rec.update(sent=ok, simulated=not ok,
                       detail=rec["detail"] + ("Posted to Slack webhook." if ok else f"webhook HTTP {resp.status}"))
            return rec
        except (error.URLError, error.HTTPError, OSError) as e:
            rec["detail"] += f"webhook failed: {e}"
            return rec

    rec["detail"] = rec["detail"] or "Slack not connected — recorded, not sent."
    return rec


def _gmail(subject: str, body: str, target: str | None):
    to = (target or os.environ.get("GMAIL_TO") or os.environ.get("GMAIL_ADDRESS") or "").strip()
    rec = {"channel": "gmail", "target": to, "subject": subject,
           "body": body, "sent": False, "simulated": True, "detail": ""}

    # 1) OAuth (Gmail API)
    if oauth_token("google") and to:
        r = gmail_conn.send_message(to, subject, body)
        if r.get("sent"):
            rec.update(sent=True, simulated=False, detail=f"Emailed {to} via Gmail API (OAuth).")
            return rec
        rec["detail"] = f"Gmail API error: {r.get('detail', 'unknown')} — "

    # 2) SMTP app-password
    addr = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if addr and pw and to:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject; msg["From"] = addr; msg["To"] = to
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=15) as s:
                s.login(addr, pw)
                s.sendmail(addr, [to], msg.as_string())
            rec.update(sent=True, simulated=False, detail=rec["detail"] + f"Emailed {to} via SMTP app-password.")
            return rec
        except (smtplib.SMTPException, OSError) as e:
            rec["detail"] += f"SMTP failed: {e}"
            return rec

    rec["detail"] = rec["detail"] or "Gmail not connected — recorded, not sent."
    return rec


def send(channel: str, subject: str, body: str, target: str | None = None) -> dict:
    """Send a confirmation on the requested channel(s): slack | gmail | both | none."""
    channel = (channel or "slack").strip().lower()
    if channel == "none":
        return {"channel": "none", "target": target, "subject": subject, "body": body,
                "sent": False, "simulated": True, "detail": "No confirmation channel configured."}
    if channel == "both":
        s, g = _slack(subject, body, target), _gmail(subject, body, None)
        return {"channel": "both", "target": target, "subject": subject, "body": body,
                "sent": s["sent"] or g["sent"], "simulated": s["simulated"] and g["simulated"],
                "detail": f"slack: {s['detail']} | gmail: {g['detail']}", "channels": [s, g]}
    if channel == "gmail":
        return _gmail(subject, body, target)
    return _slack(subject, body, target)
