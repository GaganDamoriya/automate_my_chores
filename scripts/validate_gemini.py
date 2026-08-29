#!/usr/bin/env python3
"""Validate the Gemini path for BOTH backends (AI Studio key OR Vertex AI).

Prefers the google-genai SDK if installed (works for Vertex via your Cloud login);
falls back to a zero-install stdlib REST check for AI Studio keys.

Checks:
  [1] generateContent  -> is the model reachable with your creds?
  [2] function-calling -> does the model emit a tool call? (the ADK mechanism)

Config comes from env or ./.env:
  AI Studio:  GEMINI_API_KEY, GEMINI_MODEL
  Vertex   :  GOOGLE_GENAI_USE_VERTEXAI=TRUE, GOOGLE_CLOUD_PROJECT,
              GOOGLE_CLOUD_LOCATION (default us-central1), GEMINI_MODEL
              + `gcloud auth application-default login` first.

Run:  python3 scripts/validate_gemini.py
"""
import os, sys, json, urllib.request, urllib.error

TOOL = {
    "name": "find_repeated_sequences",
    "description": "Mine an activity log for repeated cross-tool workflows.",
    "parameters": {"type": "object", "properties": {
        "min_occurrences": {"type": "integer", "description": "min repetitions"}}},
}


def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if " #" in v:
            v = v.split(" #", 1)[0].strip()
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def clean(v, default=""):
    return (v or default).split("#")[0].strip().split()[0] if (v or default) else default


def via_genai(model):
    """Use the google-genai SDK (handles Vertex + AI Studio from env)."""
    from google import genai
    from google.genai import types
    client = genai.Client()  # reads GOOGLE_GENAI_USE_VERTEXAI / project / location / key

    r1 = client.models.generate_content(model=model, contents="Reply with exactly: VALIDATION_OK")
    print(f"[1] generateContent : PASS -> {r1.text.strip()!r}")

    cfg = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[TOOL])],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")),
    )
    r2 = client.models.generate_content(
        model=model, contents="Find the repeated workflows in the activity log. Use the tool.", config=cfg)
    fc = None
    for part in (r2.candidates[0].content.parts or []):
        if getattr(part, "function_call", None):
            fc = part.function_call; break
    if fc and fc.name == "find_repeated_sequences":
        print(f"[2] function-calling: PASS -> model called {fc.name}({dict(fc.args)})")
        return True
    print(f"[2] function-calling: FAIL -> no tool call returned")
    return False


def via_rest(model):
    """Zero-install fallback: AI Studio REST (needs GEMINI_API_KEY)."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("FAIL: no GEMINI_API_KEY for REST fallback"); return False
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def post(payload):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            try: return e.code, json.load(e)
            except Exception: return e.code, {"error": {"message": e.read().decode()[:160]}}
        except Exception as e:
            return None, {"error": {"message": f"{type(e).__name__}: {e}"}}

    ok = True
    code, body = post({"contents": [{"parts": [{"text": "Reply with exactly: VALIDATION_OK"}]}]})
    if code == 200 and body.get("candidates"):
        print(f"[1] generateContent : PASS -> {body['candidates'][0]['content']['parts'][0]['text'].strip()!r}")
    else:
        ok = False; e = body.get("error", {})
        print(f"[1] generateContent : FAIL http={code} {e.get('status','')} {e.get('message','')[:150]}")
    code, body = post({"contents": [{"parts": [{"text": "Find the repeated workflows. Use the tool."}]}],
                       "tools": [{"functionDeclarations": [TOOL]}],
                       "toolConfig": {"functionCallingConfig": {"mode": "ANY"}}})
    fc = None
    if code == 200:
        for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "functionCall" in part: fc = part["functionCall"]; break
    if fc:
        print(f"[2] function-calling: PASS -> model called {fc.get('name')}({fc.get('args', {})})")
    else:
        ok = False; e = body.get("error", {})
        print(f"[2] function-calling: FAIL http={code} {e.get('status','')} {e.get('message','')[:150]}")
    return ok


def main():
    load_dotenv()
    model = clean(os.environ.get("GEMINI_MODEL"), "gemini-2.5-flash")
    vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() in ("TRUE", "1")
    backend = f"Vertex AI (project {os.environ.get('GOOGLE_CLOUD_PROJECT','?')}, " \
              f"{clean(os.environ.get('GOOGLE_CLOUD_LOCATION'),'us-central1')})" if vertex else "AI Studio (API key)"
    print(f"Backend: {backend}\nModel:   {model}\n")
    try:
        from google import genai  # noqa: F401
        ok = via_genai(model)
    except ImportError:
        if vertex:
            print("google-genai not installed but Vertex mode is on — install it: pip install google-genai")
            return 2
        print("(google-genai not installed; using stdlib REST fallback)\n")
        ok = via_rest(model)
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {str(e)[:220]}")
        if "PERMISSION_DENIED" in str(e) or "403" in str(e):
            print("  hint: enable the Vertex AI API (aiplatform.googleapis.com) on the project,")
            print("        and run: gcloud auth application-default login")
        ok = False
    print("\nRESULT:", "ALL PASS — the agent path works on this backend." if ok else "see failures above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
