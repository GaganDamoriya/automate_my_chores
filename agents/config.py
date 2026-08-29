import os
# Gemini model for all agents. 3.5 Flash is stable; 3.7 Flash is the newer
# agentic-tuned option — switch via env without touching code.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").split("#")[0].strip().split()[0]
