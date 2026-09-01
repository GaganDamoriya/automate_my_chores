"""Single-user OAuth token store (SQLite, stdlib).

One row per provider — this is a localhost, single-user demo, so tokens are keyed by
provider name alone (no user table). Lives in the same DB file as the engine (RUN_DB).
Nothing here ever returns a raw token to the UI; `list_connections()` is the safe view.
"""
import os, json, sqlite3, threading
from datetime import datetime, timezone

DB_PATH = os.environ.get("RUN_DB", os.path.join(os.getcwd(), "runs.sqlite"))
_LOCK = threading.Lock()

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _LOCK, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS credentials(
            provider TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT,
            token_type TEXT, scope TEXT, expires_at TEXT, meta TEXT, updated_at TEXT)""")

def save_token(provider: str, access_token: str, refresh_token: str = None,
               token_type: str = "Bearer", scope: str = "", expires_at: str = None,
               meta: dict = None):
    """Insert or update a provider's tokens. Keeps an existing refresh_token if the
    provider didn't return a new one (Google only sends it on first consent)."""
    with _LOCK, _conn() as c:
        existing = c.execute("SELECT refresh_token, meta FROM credentials WHERE provider=?",
                             (provider,)).fetchone()
        if refresh_token is None and existing:
            refresh_token = existing["refresh_token"]
        merged = {}
        if existing and existing["meta"]:
            merged.update(json.loads(existing["meta"]))
        if meta:
            merged.update(meta)
        c.execute("""INSERT INTO credentials(provider,access_token,refresh_token,token_type,
            scope,expires_at,meta,updated_at) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(provider) DO UPDATE SET access_token=excluded.access_token,
            refresh_token=excluded.refresh_token, token_type=excluded.token_type,
            scope=excluded.scope, expires_at=excluded.expires_at, meta=excluded.meta,
            updated_at=excluded.updated_at""",
            (provider, access_token, refresh_token, token_type, scope, expires_at,
             json.dumps(merged), _now()))

def get_token(provider: str):
    with _conn() as c:
        r = c.execute("SELECT * FROM credentials WHERE provider=?", (provider,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["meta"] = json.loads(d["meta"] or "{}")
        return d

def delete_token(provider: str):
    with _LOCK, _conn() as c:
        c.execute("DELETE FROM credentials WHERE provider=?", (provider,))
    return True

def is_connected(provider: str) -> bool:
    return get_token(provider) is not None

def list_connections() -> list:
    """Safe, non-sensitive view for the UI — never includes tokens."""
    with _conn() as c:
        rows = c.execute("SELECT provider, scope, meta, updated_at FROM credentials").fetchall()
    by_provider = {}
    for r in rows:
        meta = json.loads(r["meta"] or "{}")
        by_provider[r["provider"]] = {
            "provider": r["provider"], "connected": True,
            "account": meta.get("account") or meta.get("team") or meta.get("login") or "",
            "scope": r["scope"], "updated_at": r["updated_at"],
        }
    return by_provider
