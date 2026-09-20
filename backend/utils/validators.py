"""
Request validation helpers for the /api/tts endpoint.

Centralising validation here keeps routes.py thin and makes the rules easy
to unit test in isolation from Flask/gTTS.
"""

from typing import Optional, Tuple

from config import Config
from services import tts_service


class ValidationError(Exception):
    """Raised with a user-facing message and the HTTP status code to return."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_tts_payload(data: Optional[dict]) -> Tuple[str, str, str, bool]:
    """
    Validate the JSON body of POST /api/tts.

    Returns the cleaned (text, language, voice, auto_translate) tuple on
    success, or raises ValidationError with a descriptive message and
    status code on failure.
    """
    if data is None or not isinstance(data, dict):
        raise ValidationError(
            "Request body must be valid JSON with 'text', 'language' and 'voice' fields.",
            400,
        )

    text = data.get("text")
    language = data.get("language")
    voice = data.get("voice")

    # --- text ---
    if text is None or not isinstance(text, str):
        raise ValidationError("Field 'text' is required and must be a string.", 400)

    text = text.strip()
    if len(text) == 0:
        raise ValidationError("Text must not be empty.", 400)

    if len(text) > Config.MAX_TEXT_LENGTH:
        raise ValidationError(
            f"Text exceeds the maximum allowed length of {Config.MAX_TEXT_LENGTH} characters "
            f"(received {len(text)}).",
            400,
        )

    # --- language ---
    if not language or not isinstance(language, str):
        raise ValidationError("Field 'language' is required and must be a string.", 400)

    if not tts_service.is_valid_language(language):
        raise ValidationError(f"Language '{language}' is not supported.", 400)

    # --- voice ---
    if not voice or not isinstance(voice, str):
        raise ValidationError("Field 'voice' is required and must be a string.", 400)

    if not tts_service.is_valid_voice(language, voice):
        raise ValidationError(
            f"Voice '{voice}' is not available for language '{language}'.", 400
        )

    # --- auto_translate (optional, defaults to False) ---
    auto_translate = data.get("auto_translate", False)
    if not isinstance(auto_translate, bool):
        raise ValidationError("Field 'auto_translate' must be a boolean.", 400)

    return text, language, voice, auto_translate
