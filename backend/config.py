"""
Application configuration.

All values can be overridden using environment variables (see .env.example).
Never hard-code secrets here — this file only reads them from the environment.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file (if present) into the process environment.
load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Server ---
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = _get_bool("FLASK_DEBUG", True)

    # --- CORS ---
    # Comma-separated list of allowed frontend origins.
    FRONTEND_ORIGINS = [
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
        if origin.strip()
    ]

    # --- Text validation ---
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", 500))

    # --- Audio storage ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GENERATED_AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
    # How long a generated audio file is kept before being cleaned up (minutes).
    AUDIO_RETENTION_MINUTES = int(os.getenv("AUDIO_RETENTION_MINUTES", 30))

    # --- Rate limiting (see security considerations in the project plan) ---
    # Applied to POST /api/tts to prevent abuse of the underlying TTS service.
    RATE_LIMIT_TTS = os.getenv("RATE_LIMIT_TTS", "10 per minute")


os.makedirs(Config.GENERATED_AUDIO_DIR, exist_ok=True)
