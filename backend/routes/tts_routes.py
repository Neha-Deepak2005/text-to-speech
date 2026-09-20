"""
API routes for the Text-to-Speech application.

Endpoints (per the project plan):
  POST /api/tts      - generate speech from text
  GET  /api/voices   - list available voices (optionally filtered by language)
  GET  /api/health   - health check
"""

from flask import Blueprint, jsonify, request, current_app

from config import Config
from extensions import limiter
from services import translation_service, tts_service
from utils.validators import ValidationError, validate_tts_payload

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _error_response(message: str, status_code: int):
    return jsonify({"success": False, "error": message}), status_code


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@api_bp.get("/voices")
def voices():
    language = request.args.get("language")

    if language is not None and not tts_service.is_valid_language(language):
        return _error_response(f"Language '{language}' is not supported.", 400)

    return (
        jsonify(
            {
                "success": True,
                "languages": tts_service.get_languages(),
                "voices": tts_service.get_voices(language),
                "language_groups": tts_service.get_language_groups(),
                # Exposed so the frontend can stay in sync with the backend's
                # actual limit instead of hard-coding its own copy.
                "max_text_length": Config.MAX_TEXT_LENGTH,
            }
        ),
        200,
    )


@api_bp.post("/tts")
@limiter.limit(Config.RATE_LIMIT_TTS)
def text_to_speech():
    if not request.is_json:
        return _error_response(
            "Content-Type must be 'application/json'.", 400
        )

    try:
        data = request.get_json(silent=True)
        text, language, voice, auto_translate = validate_tts_payload(data)
    except ValidationError as exc:
        return _error_response(exc.message, exc.status_code)

    translated_text = None
    if auto_translate:
        try:
            translated_text = translation_service.translate_text(text, target_language=language)
        except translation_service.TranslationServiceError as exc:
            current_app.logger.warning("Translation failed: %s", exc.message)
            return _error_response(exc.message, exc.status_code)

    text_for_speech = translated_text if translated_text else text

    try:
        filename = tts_service.generate_speech(text_for_speech, language, voice)
    except tts_service.TTSServiceError as exc:
        current_app.logger.warning("TTS generation failed: %s", exc.message)
        return _error_response(exc.message, exc.status_code)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        current_app.logger.exception("Unexpected error generating speech")
        return _error_response("An unexpected server error occurred.", 500)

    response = {
        "success": True,
        "audio_url": f"/audio/{filename}",
    }
    if translated_text:
        response["original_text"] = text
        response["translated_text"] = translated_text

    return jsonify(response), 200
