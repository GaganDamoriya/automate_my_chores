"""OAuth connect/disconnect routes (single-user local).

Flow: GET /auth/{provider}/login  -> 302 to the provider's consent screen
      GET /auth/{provider}/callback -> exchange the code, store tokens, 302 back to the web app
      POST /auth/{provider}/disconnect -> forget the tokens
      GET /auth/connections -> status for the Connections page (never returns tokens)
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from .. import oauth, credentials

router = APIRouter(prefix="/auth", tags=["auth"])

def _web(path):
    return f"{oauth.WEB_BASE}{path}"

@router.get("/connections")
def connections():
    connected = credentials.list_connections()
    out = []
    for p, cfg in oauth.PROVIDERS.items():
        c = connected.get(p)
        out.append({
            "provider": p,
            "label": cfg["label"],
            "configured": oauth.is_configured(p),
            "connected": bool(c),
            "account": (c or {}).get("account", ""),
            "scope": cfg["scope"],
        })
    return {"connections": out}

@router.get("/{provider}/login")
def login(provider: str):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(404, "unknown provider")
    if not oauth.is_configured(provider):
        return RedirectResponse(_web(f"/connections?error=not_configured&provider={provider}"))
    state = oauth.new_state(provider)
    return RedirectResponse(oauth.authorize_url(provider, state))

@router.get("/{provider}/callback")
def callback(provider: str, code: str = None, state: str = None, error: str = None):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(404, "unknown provider")
    if error:
        return RedirectResponse(_web(f"/connections?error={error}&provider={provider}"))
    if not code or oauth.pop_state(state) != provider:
        return RedirectResponse(_web(f"/connections?error=bad_state&provider={provider}"))
    try:
        oauth.exchange_code(provider, code)
    except oauth.OAuthError as e:
        return RedirectResponse(_web(f"/connections?error=exchange_failed&provider={provider}"))
    return RedirectResponse(_web(f"/connections?connected={provider}"))

@router.post("/{provider}/disconnect")
def disconnect(provider: str):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(404, "unknown provider")
    credentials.delete_token(provider)
    return {"ok": True, "provider": provider}
