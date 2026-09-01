"""OAuth 2.0 core for Google, Slack, GitHub, and Jira (Atlassian) — stdlib only.

Single-user local flow: /auth/{provider}/login -> consent -> /auth/{provider}/callback
-> exchange_code() stores tokens via `credentials`. `get_valid_token(provider)` returns a
live access token, refreshing transparently when it has expired (Google, Atlassian).

Register the four apps and set client id/secret in .env; the redirect URI each app must
allow is  {OAUTH_REDIRECT_BASE}/auth/{provider}/callback  (default http://localhost:8000).
"""
import os, json, time, secrets
from datetime import datetime, timezone, timedelta
from urllib import request, parse, error
from . import credentials

REDIRECT_BASE = os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8000")
WEB_BASE = os.environ.get("WEB_BASE", "http://localhost:3000")

class OAuthError(Exception):
    pass

# provider -> config. token_style: how the token endpoint wants the body.
PROVIDERS = {
    "google": {
        "label": "Google (Gmail + Sheets)",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "openid email https://www.googleapis.com/auth/gmail.send "
                 "https://www.googleapis.com/auth/spreadsheets",
        "id_env": "GOOGLE_OAUTH_CLIENT_ID", "secret_env": "GOOGLE_OAUTH_CLIENT_SECRET",
        "extra_auth": {"access_type": "offline", "prompt": "consent",
                       "include_granted_scopes": "true"},
        "token_style": "form", "refreshable": True,
    },
    "slack": {
        "label": "Slack",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scope": "chat:write,channels:read",
        "id_env": "SLACK_CLIENT_ID", "secret_env": "SLACK_CLIENT_SECRET",
        "extra_auth": {}, "token_style": "form", "refreshable": False,
    },
    "github": {
        "label": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scope": "repo read:user",
        "id_env": "GITHUB_CLIENT_ID", "secret_env": "GITHUB_CLIENT_SECRET",
        "extra_auth": {}, "token_style": "form_json_accept", "refreshable": False,
    },
    "jira": {
        "label": "Jira (Atlassian)",
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "scope": "read:jira-work read:jira-user offline_access",
        "id_env": "ATLASSIAN_CLIENT_ID", "secret_env": "ATLASSIAN_CLIENT_SECRET",
        "extra_auth": {"audience": "api.atlassian.com", "prompt": "consent"},
        "token_style": "json", "refreshable": True,
    },
}

# --- small helpers ---------------------------------------------------------

def _now_dt():
    return datetime.now(timezone.utc)

def _cfg(provider):
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise OAuthError(f"unknown provider '{provider}'")
    return cfg

def client_id(provider):
    return os.environ.get(_cfg(provider)["id_env"], "").strip()

def client_secret(provider):
    return os.environ.get(_cfg(provider)["secret_env"], "").strip()

def is_configured(provider) -> bool:
    return bool(client_id(provider) and client_secret(provider))

def redirect_uri(provider):
    return f"{REDIRECT_BASE}/auth/{provider}/callback"

def _post(url, data, headers=None, as_json=False):
    body = json.dumps(data).encode() if as_json else parse.urlencode(data).encode()
    h = {"Accept": "application/json"}
    h["Content-Type"] = "application/json" if as_json else "application/x-www-form-urlencoded"
    if headers:
        h.update(headers)
    req = request.Request(url, data=body, headers=h)
    try:
        with request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode() or "{}")
    except error.HTTPError as e:
        raise OAuthError(f"{url} -> HTTP {e.code}: {e.read().decode()[:200]}")
    except (error.URLError, OSError) as e:
        raise OAuthError(f"{url} -> {e}")

def _get_json(url, token):
    req = request.Request(url, headers={"Authorization": f"Bearer {token}",
                                        "Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode() or "{}")
    except (error.HTTPError, error.URLError, OSError):
        return {}

# --- CSRF state (in-memory, TTL) ------------------------------------------
_STATES = {}
_STATE_TTL = 600

def new_state(provider):
    s = secrets.token_urlsafe(24)
    _STATES[s] = (provider, time.time())
    # opportunistic cleanup
    for k, (_, ts) in list(_STATES.items()):
        if time.time() - ts > _STATE_TTL:
            _STATES.pop(k, None)
    return s

def pop_state(state):
    entry = _STATES.pop(state, None)
    if not entry:
        return None
    provider, ts = entry
    if time.time() - ts > _STATE_TTL:
        return None
    return provider

# --- flow ------------------------------------------------------------------

def authorize_url(provider, state):
    cfg = _cfg(provider)
    if not is_configured(provider):
        raise OAuthError(f"{provider} OAuth not configured — set {cfg['id_env']} and {cfg['secret_env']}")
    params = {
        "client_id": client_id(provider),
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        **cfg.get("extra_auth", {}),
    }
    return cfg["authorize_url"] + "?" + parse.urlencode(params)

def _expires_at(token_resp):
    exp = token_resp.get("expires_in")
    if not exp:
        return None
    return (_now_dt() + timedelta(seconds=int(exp))).strftime("%Y-%m-%dT%H:%M:%SZ")

def exchange_code(provider, code):
    cfg = _cfg(provider)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(provider),
        "client_id": client_id(provider),
        "client_secret": client_secret(provider),
    }
    style = cfg["token_style"]
    resp = _post(cfg["token_url"], data, as_json=(style == "json"))
    if provider == "slack" and not resp.get("ok", False):
        raise OAuthError(f"slack oauth failed: {resp.get('error')}")
    access = resp.get("access_token")
    if not access:
        raise OAuthError(f"{provider}: no access_token in response ({list(resp)})")
    meta = _fetch_meta(provider, access, resp)
    credentials.save_token(
        provider, access_token=access, refresh_token=resp.get("refresh_token"),
        token_type=resp.get("token_type", "Bearer"), scope=resp.get("scope", cfg["scope"]),
        expires_at=_expires_at(resp), meta=meta)
    return meta

def refresh(provider):
    cfg = _cfg(provider)
    tok = credentials.get_token(provider)
    if not (tok and tok.get("refresh_token") and cfg["refreshable"]):
        return tok["access_token"] if tok else None
    data = {
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": client_id(provider),
        "client_secret": client_secret(provider),
    }
    resp = _post(cfg["token_url"], data, as_json=(cfg["token_style"] == "json"))
    access = resp.get("access_token")
    if not access:
        raise OAuthError(f"{provider} refresh failed ({list(resp)})")
    credentials.save_token(
        provider, access_token=access, refresh_token=resp.get("refresh_token"),
        token_type=resp.get("token_type", "Bearer"),
        scope=resp.get("scope", tok.get("scope", "")), expires_at=_expires_at(resp))
    return access

def _expired(tok) -> bool:
    exp = tok.get("expires_at")
    if not exp:
        return False
    try:
        dt = datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return _now_dt() >= (dt - timedelta(seconds=60))  # refresh a minute early

def get_valid_token(provider):
    """Return a usable access token, refreshing if expired. None if not connected."""
    tok = credentials.get_token(provider)
    if not tok:
        return None
    if _expired(tok) and tok.get("refresh_token"):
        try:
            return refresh(provider)
        except OAuthError:
            return tok["access_token"]
    return tok["access_token"]

def cloudid(provider="jira"):
    """Jira: the Atlassian cloud id stored at connect time (needed for REST calls)."""
    tok = credentials.get_token(provider)
    return (tok or {}).get("meta", {}).get("cloudid")

# --- provider account labels ----------------------------------------------

def _fetch_meta(provider, access_token, token_resp):
    meta = {}
    try:
        if provider == "google":
            info = _get_json("https://openidconnect.googleapis.com/v1/userinfo", access_token)
            meta["account"] = info.get("email", "")
        elif provider == "slack":
            meta["team"] = (token_resp.get("team") or {}).get("name", "")
            meta["account"] = meta["team"]
        elif provider == "github":
            info = _get_json("https://api.github.com/user", access_token)
            meta["login"] = info.get("login", "")
            meta["account"] = info.get("login", "")
        elif provider == "jira":
            res = _get_json("https://api.atlassian.com/oauth/token/accessible-resources", access_token)
            if isinstance(res, list) and res:
                meta["cloudid"] = res[0].get("id")
                meta["account"] = res[0].get("name") or res[0].get("url", "")
    except Exception:  # noqa: BLE001 — meta is best-effort; never block the connect
        pass
    return meta
