"""Mock Slack connector (writes to an in-memory sink)."""
_SENT = []

def post_message(channel: str, text: str) -> dict:
    msg = {"channel": channel, "text": text, "ok": True}
    _SENT.append(msg)
    return msg

def sent():
    return list(_SENT)
