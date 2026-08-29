"""Run the real ADK discovery pipeline from the terminal and print the live feed.

    python3 -m venv .venv-adk && source .venv-adk/bin/activate
    pip install google-adk google-genai
    set -a; source .env; set +a
    export GOOGLE_API_KEY="$GEMINI_API_KEY"
    python -m agents.run_local
"""
import asyncio
from agents import runtime


async def main():
    if not runtime.adk_available():
        print("google-adk not installed or GEMINI_API_KEY not set — nothing to run.")
        print("  pip install google-adk google-genai && export GEMINI_API_KEY=...")
        return
    try:
        async for line in runtime.stream_events():
            print(f"[{line['agent']:>18}] {line['text']}")
    except Exception as e:  # noqa: BLE001 — surface a friendly message, not a stack dump
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            print("\n⏳ Hit the Gemini FREE-TIER rate limit (5 requests/minute).")
            print("   The pipeline WAS running correctly — the agents made real Gemini")
            print("   calls and tool calls before the cap. To run it end to end:")
            print("     • enable billing on the API key (paid tier lifts the 5/min cap), or")
            print("     • wait ~60s and re-run, or try GEMINI_MODEL=gemini-2.5-flash")
        else:
            raise


if __name__ == "__main__":
    asyncio.run(main())
