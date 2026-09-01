"""Connector base: seed loader + shared OAuth-token / HTTP helpers (stdlib).

Connectors call a real provider API when an OAuth token is stored, and fall back to
the simulated seed path otherwise. `oauth_token(provider)` bridges to the API's token
store lazily (no import-time coupling, works in standalone tests too).
"""
import json, os
from urllib import request, parse, error

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.environ.get("SEED_DIR", os.path.join(_REPO, "seed", "data"))

def load(name):
    with open(os.path.join(_DATA, name)) as f:
        return json.load(f)

def oauth_token(provider: str):
    """A live access token for the provider, or None. Never raises."""
    try:
        import sys
        if _REPO not in sys.path:
            sys.path.insert(0, _REPO)
        from api.app import oauth
        return oauth.get_valid_token(provider)
    except Exception:  # noqa: BLE001
        return None

def jira_cloudid():
    try:
        import sys
        if _REPO not in sys.path:
            sys.path.insert(0, _REPO)
        from api.app import oauth
        return oauth.cloudid("jira")
    except Exception:  # noqa: BLE001
        return None

def _do(req):
    try:
        with request.urlopen(req, timeout=20) as r:
            raw = r.read().decode() or "{}"
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else {"raw": raw})
    except error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}
    except (error.URLError, OSError) as e:
        return 0, {"error": str(e)}

def get_json(url: str, token: str = None, headers: dict = None):
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    return _do(request.Request(url, headers=h))

def post_json(url: str, payload: dict, token: str = None, headers: dict = None):
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    return _do(request.Request(url, data=json.dumps(payload).encode(), headers=h))
