"""
Text-to-Speech service.

Wraps the gTTS (Google Translate Text-to-Speech) library and is the single
place in the backend that knows about:
  - which languages/voices are offered,
  - how a "voice" maps to gTTS parameters (regional variant via `lang_code`,
    English accent via `tld`, pace via `slow`),
  - how audio files are generated, named and cleaned up.

gTTS provides one synthetic voice per language (no true male/female
selection). To still give users a meaningful "voice" choice, each language
offers a few *presets*:
  - For English, `tld` (translate.google.<tld>) genuinely changes accent
    (US/UK/India/Australia) — this is the one case gTTS documents as
    reliable.
  - For the handful of languages gTTS exposes as distinct codes (French
    Canada, Portuguese Portugal, Chinese Simplified/Taiwan), the voice uses
    that real `lang_code` rather than a tld guess.
  - For every language, a "Slow & Clear" preset using gTTS's `slow` flag.
This is documented honestly in the README — the app never claims a
"male/female" voice, or a regional accent, it can't actually deliver.
"""

import os
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from gtts import gTTS
from gtts.lang import tts_langs

from config import Config


class TTSServiceError(Exception):
    """Base class for expected, user-facing TTS service errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnsupportedLanguageError(TTSServiceError):
    def __init__(self, language: str):
        super().__init__(f"Language '{language}' is not supported.", 400)


class UnsupportedVoiceError(TTSServiceError):
    def __init__(self, voice: str, language: str):
        super().__init__(
            f"Voice '{voice}' is not available for language '{language}'.", 400
        )


class TTSProviderError(TTSServiceError):
    """Raised when the underlying TTS provider (Google) fails or is unreachable."""

    def __init__(self, message: str = "The Text-to-Speech provider is currently unavailable."):
        super().__init__(message, 503)


@dataclass
class Voice:
    id: str
    label: str
    tld: str = "com"
    slow: bool = False
    # The actual code passed to gTTS's `lang` parameter. Defaults to the
    # voice's parent language key when not set — only overridden for the
    # handful of languages gTTS exposes as a genuinely distinct code
    # (e.g. "fr-CA", "pt-PT", "zh-TW") rather than a same-language accent.
    lang_code: Optional[str] = None


# --- Supported languages -----------------------------------------------
# A curated mix of Indian and widely-spoken foreign languages, all backed
# by real gTTS + deep-translator support (verified against both libraries'
# supported-language lists) — not the full ~45-language gTTS catalog, to
# keep the UI usable.
LANGUAGES = {
    # --- Indian languages ---
    "hi": "Hindi",
    "gu": "Gujarati",
    "mr": "Marathi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "ne": "Nepali",
    # --- English + other foreign languages ---
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "nl": "Dutch",
    "tr": "Turkish",
}

# Grouping used by the frontend to render <optgroup> sections instead of one
# long flat dropdown. Purely a UI hint — /api/tts and /api/voices?language=
# don't care about grouping, only LANGUAGES/VOICES above.
LANGUAGE_GROUPS = {
    "Indian Languages": ["hi", "gu", "mr", "bn", "ta", "te", "kn", "ml", "pa", "ur", "ne"],
    "Other Languages": [
        "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "nl", "tr",
    ],
}

# --- Voice presets per language -----------------------------------------
# Every language gets a "Standard" and "Slow & Clear" preset at minimum.
# A few get additional presets where gTTS supports a real regional
# accent/code (English tld variants; French/Portuguese/Chinese distinct
# lang codes) — see the module docstring.
VOICES: dict[str, list[Voice]] = {
    "en": [
        Voice("en-us-standard", "English (US) – Standard", tld="com"),
        Voice("en-uk-standard", "English (UK) – Standard", tld="co.uk"),
        Voice("en-in-standard", "English (India) – Standard", tld="co.in"),
        Voice("en-au-standard", "English (Australia) – Standard", tld="com.au"),
        Voice("en-us-slow", "English (US) – Slow & Clear", tld="com", slow=True),
    ],
    "hi": [
        Voice("hi-standard", "Hindi – Standard"),
        Voice("hi-slow", "Hindi – Slow & Clear", slow=True),
    ],
    "gu": [
        Voice("gu-standard", "Gujarati – Standard"),
        Voice("gu-slow", "Gujarati – Slow & Clear", slow=True),
    ],
    "mr": [
        Voice("mr-standard", "Marathi – Standard"),
        Voice("mr-slow", "Marathi – Slow & Clear", slow=True),
    ],
    "bn": [
        Voice("bn-standard", "Bengali – Standard"),
        Voice("bn-slow", "Bengali – Slow & Clear", slow=True),
    ],
    "ta": [
        Voice("ta-standard", "Tamil – Standard"),
        Voice("ta-slow", "Tamil – Slow & Clear", slow=True),
    ],
    "te": [
        Voice("te-standard", "Telugu – Standard"),
        Voice("te-slow", "Telugu – Slow & Clear", slow=True),
    ],
    "kn": [
        Voice("kn-standard", "Kannada – Standard"),
        Voice("kn-slow", "Kannada – Slow & Clear", slow=True),
    ],
    "ml": [
        Voice("ml-standard", "Malayalam – Standard"),
        Voice("ml-slow", "Malayalam – Slow & Clear", slow=True),
    ],
    "pa": [
        Voice("pa-standard", "Punjabi – Standard"),
        Voice("pa-slow", "Punjabi – Slow & Clear", slow=True),
    ],
    "ur": [
        Voice("ur-standard", "Urdu – Standard"),
        Voice("ur-slow", "Urdu – Slow & Clear", slow=True),
    ],
    "ne": [
        Voice("ne-standard", "Nepali – Standard"),
        Voice("ne-slow", "Nepali – Slow & Clear", slow=True),
    ],
    "es": [
        Voice("es-standard", "Spanish – Standard"),
        Voice("es-slow", "Spanish – Slow & Clear", slow=True),
    ],
    "fr": [
        Voice("fr-fr-standard", "French (France) – Standard", lang_code="fr"),
        Voice("fr-ca-standard", "French (Canada) – Standard", lang_code="fr-CA"),
        Voice("fr-fr-slow", "French – Slow & Clear", lang_code="fr", slow=True),
    ],
    "de": [
        Voice("de-standard", "German – Standard"),
        Voice("de-slow", "German – Slow & Clear", slow=True),
    ],
    "it": [
        Voice("it-standard", "Italian – Standard"),
        Voice("it-slow", "Italian – Slow & Clear", slow=True),
    ],
    "pt": [
        Voice("pt-br-standard", "Portuguese (Brazil) – Standard", lang_code="pt"),
        Voice("pt-pt-standard", "Portuguese (Portugal) – Standard", lang_code="pt-PT"),
        Voice("pt-br-slow", "Portuguese – Slow & Clear", lang_code="pt", slow=True),
    ],
    "ru": [
        Voice("ru-standard", "Russian – Standard"),
        Voice("ru-slow", "Russian – Slow & Clear", slow=True),
    ],
    "ja": [
        Voice("ja-standard", "Japanese – Standard"),
        Voice("ja-slow", "Japanese – Slow & Clear", slow=True),
    ],
    "ko": [
        Voice("ko-standard", "Korean – Standard"),
        Voice("ko-slow", "Korean – Slow & Clear", slow=True),
    ],
    "zh": [
        Voice("zh-cn-standard", "Chinese (Simplified) – Standard", lang_code="zh-CN"),
        Voice("zh-tw-standard", "Chinese (Taiwan) – Standard", lang_code="zh-TW"),
        Voice("zh-cn-slow", "Chinese – Slow & Clear", lang_code="zh-CN", slow=True),
    ],
    "ar": [
        Voice("ar-standard", "Arabic – Standard"),
        Voice("ar-slow", "Arabic – Slow & Clear", slow=True),
    ],
    "nl": [
        Voice("nl-standard", "Dutch – Standard"),
        Voice("nl-slow", "Dutch – Slow & Clear", slow=True),
    ],
    "tr": [
        Voice("tr-standard", "Turkish – Standard"),
        Voice("tr-slow", "Turkish – Slow & Clear", slow=True),
    ],
}


def get_languages() -> dict:
    return LANGUAGES


def get_language_groups() -> dict:
    return LANGUAGE_GROUPS


def get_voices(language: Optional[str] = None) -> dict:
    """Return voices grouped by language, or just for one language if given."""
    if language is None:
        return {
            lang: [v.__dict__ for v in voices] for lang, voices in VOICES.items()
        }
    if language not in VOICES:
        raise UnsupportedLanguageError(language)
    return {language: [v.__dict__ for v in VOICES[language]]}


def is_valid_language(language: str) -> bool:
    return isinstance(language, str) and language in LANGUAGES


def is_valid_voice(language: str, voice_id: str) -> bool:
    if not is_valid_language(language):
        return False
    return any(v.id == voice_id for v in VOICES.get(language, []))


def _find_voice(language: str, voice_id: str) -> Voice:
    for v in VOICES.get(language, []):
        if v.id == voice_id:
            return v
    raise UnsupportedVoiceError(voice_id, language)


def cleanup_old_audio(retention_minutes: int = None) -> int:
    """
    Delete generated audio files older than `retention_minutes`.
    Returns the number of files removed. Failures to delete a single file
    are ignored (e.g. concurrent access) so cleanup never breaks a request.
    """
    retention_minutes = retention_minutes or Config.AUDIO_RETENTION_MINUTES
    cutoff = time.time() - (retention_minutes * 60)
    removed = 0
    try:
        for name in os.listdir(Config.GENERATED_AUDIO_DIR):
            if name == ".gitkeep":
                continue
            path = os.path.join(Config.GENERATED_AUDIO_DIR, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed += 1
            except OSError:
                continue
    except FileNotFoundError:
        pass
    return removed


def generate_speech(text: str, language: str, voice_id: str) -> str:
    """
    Generate an MP3 file for `text` using the given language/voice preset.

    Returns the generated file's name (not a full path/URL — routes build
    the public URL). Raises TTSServiceError subclasses on any expected
    failure so the route layer can translate them into HTTP responses.
    """
    if not is_valid_language(language):
        raise UnsupportedLanguageError(language)

    voice = _find_voice(language, voice_id)

    # Best-effort cleanup of old files so generated_audio/ doesn't grow
    # unbounded (see security considerations: don't store audio permanently).
    cleanup_old_audio()

    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(Config.GENERATED_AUDIO_DIR, filename)

    effective_lang = voice.lang_code or language

    try:
        tts = gTTS(text=text, lang=effective_lang, tld=voice.tld, slow=voice.slow)
        tts.save(filepath)
    except ValueError as exc:
        # gTTS raises ValueError for e.g. empty text or unsupported lang codes.
        raise TTSServiceError(str(exc), 400) from exc
    except AssertionError as exc:
        raise TTSServiceError("No speech could be generated for the given text.", 400) from exc
    except Exception as exc:  # noqa: BLE001 - translate any provider/network failure
        raise TTSProviderError(f"Failed to generate speech: {exc}") from exc

    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        raise TTSProviderError("The Text-to-Speech provider returned an empty response.")

    return filename


def supported_gtts_languages() -> dict:
    """Expose the full gTTS-supported language list (diagnostic use only)."""
    try:
        return tts_langs()
    except Exception:
        return {}
