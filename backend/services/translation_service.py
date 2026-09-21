"""
Auto-translation service.

Optional pre-processing step for /api/tts: translates the user's input
text into the selected target language before it's handed to gTTS. This is
useful when the user types in one language (e.g. English) but wants the
speech spoken in another (e.g. Hindi) — gTTS itself only pronounces text
using a language's phonetics, it does not translate.

Two independent, free, no-API-key providers are used, in order:

1. GoogleTranslator (deep-translator) — same free endpoint gTTS uses.
2. MyMemoryTranslator (deep-translator) — a separate free translation
   service, used only as a fallback.

Google's free endpoint enforces a hard rate limit (5 requests/sec, 200k/day)
per source IP. On a platform like Render's free tier, the outbound IP is
shared across many unrelated apps, so that limit can be hit even when this
app alone is well within it — and, since it's shared infrastructure, simply
waiting doesn't reliably fix it. Falling back to a second, differently
rate-limited provider makes translation resilient to that: it's very
unlikely both providers are rate-limited on the same shared IP at once.
"""

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import LanguageNotSupportedException, NotValidPayload


class TranslationServiceError(Exception):
    """Raised when translation fails; carries the HTTP status to return."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# deep-translator's supported-language codes don't always match our app's
# internal language codes (used for both TTS and the UI). Only "zh" needs
# remapping for Google today — deep-translator expects "zh-CN" for Chinese.
GOOGLE_LANGUAGE_OVERRIDES = {
    "zh": "zh-CN",
}

# Kept for backwards compatibility with anything importing the old name.
TRANSLATE_LANGUAGE_OVERRIDES = GOOGLE_LANGUAGE_OVERRIDES

# MyMemory (the fallback provider) doesn't accept bare 2-letter codes like
# GoogleTranslator does — it requires a full locale code (e.g. "hi-IN", not
# "hi"). This maps every language code our app supports to its MyMemory
# equivalent. Verified against MyMemoryTranslator().get_supported_languages().
MYMEMORY_LANGUAGE_CODES = {
    "hi": "hi-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "ur": "ur-PK",
    "ne": "ne-NP",
    "en": "en-GB",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh": "zh-CN",
    "ar": "ar-SA",
    "nl": "nl-NL",
    "tr": "tr-TR",
}


def _translate_with_google(text: str, target_language: str, source_language: str) -> str:
    target = GOOGLE_LANGUAGE_OVERRIDES.get(target_language, target_language)
    return GoogleTranslator(source=source_language, target=target).translate(text)


def _translate_with_mymemory(text: str, target_language: str, source_language: str) -> str:
    target = MYMEMORY_LANGUAGE_CODES.get(target_language, target_language)
    source = source_language if source_language == "auto" else MYMEMORY_LANGUAGE_CODES.get(
        source_language, source_language
    )
    return MyMemoryTranslator(source=source, target=target).translate(text)


_PROVIDERS = (
    ("Google", _translate_with_google),
    ("MyMemory", _translate_with_mymemory),
)


def translate_text(text: str, target_language: str, source_language: str = "auto") -> str:
    """
    Translate `text` into `target_language` (one of our app's internal
    language codes). Returns the translated text.

    Tries each provider in `_PROVIDERS` in order and returns the first
    successful, non-empty result. A provider-specific error (e.g. Google's
    rate limit) moves on to the next provider rather than failing outright;
    only when every provider has failed is a `TranslationServiceError`
    raised. An invalid-language error is raised immediately, since retrying
    with a different provider can't fix a bad input.
    """
    last_error: Exception | None = None

    for provider_name, translate_fn in _PROVIDERS:
        try:
            translated = translate_fn(text, target_language, source_language)
        except (LanguageNotSupportedException, NotValidPayload) as exc:
            raise TranslationServiceError(f"Translation input was invalid: {exc}", 400) from exc
        except Exception as exc:  # noqa: BLE001 - fall through to the next provider
            last_error = exc
            continue

        if translated and translated.strip():
            return translated
        last_error = RuntimeError(f"{provider_name} returned empty text.")

    raise TranslationServiceError(
        f"Translation failed on all available providers. Please try again shortly. ({last_error})",
        503,
    )