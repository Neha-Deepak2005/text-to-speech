"""
Auto-translation service.

Optional pre-processing step for /api/tts: translates the user's input
text into the selected target language before it's handed to gTTS. This is
useful when the user types in one language (e.g. English) but wants the
speech spoken in another (e.g. Hindi) — gTTS itself only pronounces text
using a language's phonetics, it does not translate.

Uses deep-translator's GoogleTranslator, which — like gTTS — calls Google's
free translation endpoint and needs no API key.
"""

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    LanguageNotSupportedException,
    NotValidPayload,
    RequestError,
    TranslationNotFound,
)


class TranslationServiceError(Exception):
    """Raised when translation fails; carries the HTTP status to return."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# deep-translator's supported-language codes don't always match our app's
# internal language codes (used for both TTS and the UI). Only "zh" needs
# remapping today — deep-translator expects "zh-CN" for Chinese — but this
# table is the single place to add any future mismatch.
TRANSLATE_LANGUAGE_OVERRIDES = {
    "zh": "zh-CN",
}


def translate_text(text: str, target_language: str, source_language: str = "auto") -> str:
    """
    Translate `text` into `target_language` (one of our app's internal
    language codes). Returns the translated text.

    If the text is already (or ends up) identical after translation — e.g.
    the source and target language are the same — the original text is
    returned as-is.
    """
    translate_target = TRANSLATE_LANGUAGE_OVERRIDES.get(target_language, target_language)

    try:
        translated = GoogleTranslator(source=source_language, target=translate_target).translate(text)
    except (LanguageNotSupportedException, NotValidPayload) as exc:
        raise TranslationServiceError(f"Translation input was invalid: {exc}", 400) from exc
    except (RequestError, TranslationNotFound) as exc:
        raise TranslationServiceError(
            "The translation service is currently unavailable. Please try again.", 503
        ) from exc
    except Exception as exc:  # noqa: BLE001 - translate any other failure into a clean 503
        raise TranslationServiceError(f"Translation failed: {exc}", 503) from exc

    if not translated or not translated.strip():
        raise TranslationServiceError("Translation returned empty text.", 503)

    return translated
