import os
from functools import lru_cache

class Settings:
    def __init__(self):
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").split("#")[0].strip().split()[0]
        self.seed_dir = os.environ.get("SEED_DIR")  # None -> tools use repo default
        self.cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        self.use_adk = os.environ.get("USE_ADK", "0") == "1"
        # Normalize the API key so google-genai/ADK pick it up (AI Studio key).
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            os.environ.setdefault("GOOGLE_API_KEY", key)
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                              os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE"))
        # Vertex mode needs a region; default one if the user enabled Vertex.
        if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() in ("TRUE", "1"):
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

@lru_cache
def get_settings():
    return Settings()
