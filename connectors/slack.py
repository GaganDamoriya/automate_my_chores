"""Slack connector — live chat.postMessage when connected, else in-memory sink."""
from .base import oauth_token, post_json

_SENT = []

def post_message(channel: str, text: str) -> dict:
    token = oauth_token("slack")
    if token:
        status, resp = post_json("https://slack.com/api/chat.postMessage",
                                 {"channel": channel, "text": text}, token=token)
        if resp.get("ok"):
            return {"channel": channel, "text": text, "ok": True,
                    "source": "live", "ts": resp.get("ts")}
        # fall through to sink on any Slack error (e.g. not_in_channel)
        msg = {"channel": channel, "text": text, "ok": False, "source": "live",
               "error": resp.get("error", "slack_error")}
        _SENT.append(msg)
        return msg
    msg = {"channel": channel, "text": text, "ok": True, "source": "seed"}
    _SENT.append(msg)
    return msg

def sent():
    return list(_SENT)
