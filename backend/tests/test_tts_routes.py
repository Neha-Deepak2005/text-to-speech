"""
Tests for the /api/* routes.

gTTS.save() is monkeypatched in the tests that reach it, so the suite runs
fully offline (no dependency on Google's servers) while still exercising
the real Flask routing, validation and file-serving code paths.
"""

import os

import pytest


def _fake_gtts_save(monkeypatch, payload=b"FAKE_MP3_AUDIO_BYTES"):
    def fake_save(self, fp):
        with open(fp, "wb") as f:
            f.write(payload)

    monkeypatch.setattr("gtts.gTTS.save", fake_save)


def _fake_translate(monkeypatch, prefix="TRANSLATED: "):
    def fake_translate(self, text):
        return prefix + text

    monkeypatch.setattr("deep_translator.GoogleTranslator.translate", fake_translate)


def _fake_mymemory_translate(monkeypatch, prefix="MYMEMORY: "):
    def fake_translate(self, text):
        return prefix + text

    monkeypatch.setattr("deep_translator.MyMemoryTranslator.translate", fake_translate)


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


class TestVoices:
    def test_list_all_languages_and_voices(self, client):
        resp = client.get("/api/voices")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "en" in data["languages"]
        assert "hi" in data["languages"]
        assert len(data["voices"]["en"]) >= 1
        for v in data["voices"]["en"]:
            assert {"id", "label", "tld", "slow"} <= v.keys()

    def test_filter_by_language(self, client):
        resp = client.get("/api/voices?language=hi")
        assert resp.status_code == 200
        data = resp.get_json()
        assert list(data["voices"].keys()) == ["hi"]

    def test_invalid_language_returns_400(self, client):
        resp = client.get("/api/voices?language=zz")
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_indian_and_foreign_languages_present(self, client):
        resp = client.get("/api/voices")
        data = resp.get_json()
        indian = {"hi", "gu", "mr", "bn", "ta", "te", "kn", "ml", "pa", "ur", "ne"}
        foreign = {"en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "nl", "tr"}
        assert indian <= set(data["languages"].keys())
        assert foreign <= set(data["languages"].keys())
        # Every listed language must actually have at least one voice preset.
        for code in data["languages"]:
            assert len(data["voices"][code]) >= 1, f"{code} has no voices"

    @pytest.mark.parametrize(
        "language,voice_id",
        [
            ("bn", "bn-standard"),
            ("ta", "ta-standard"),
            ("te", "te-standard"),
            ("kn", "kn-standard"),
            ("ml", "ml-standard"),
            ("pa", "pa-standard"),
            ("ur", "ur-standard"),
            ("ne", "ne-standard"),
            ("ja", "ja-standard"),
            ("ko", "ko-standard"),
            ("ar", "ar-standard"),
            ("ru", "ru-standard"),
            ("tr", "tr-standard"),
            ("nl", "nl-standard"),
            ("it", "it-standard"),
        ],
    )
    def test_new_language_generates_speech(self, client, monkeypatch, language, voice_id):
        _fake_gtts_save(monkeypatch)
        resp = client.post(
            "/api/tts", json={"text": "hello", "language": language, "voice": voice_id}
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    @pytest.mark.parametrize(
        "language,voice_id,expected_lang_code",
        [
            ("fr", "fr-ca-standard", "fr-CA"),
            ("pt", "pt-pt-standard", "pt-PT"),
            ("zh", "zh-tw-standard", "zh-TW"),
            ("zh", "zh-cn-standard", "zh-CN"),
        ],
    )
    def test_regional_voice_uses_correct_gtts_lang_code(
        self, client, monkeypatch, language, voice_id, expected_lang_code
    ):
        seen = {}

        def fake_gtts_init(self, text, lang="en", **kwargs):
            seen["lang"] = lang
            self.text = text
            self.lang = lang

        def fake_save(self, fp):
            with open(fp, "wb") as f:
                f.write(b"FAKE")

        monkeypatch.setattr("gtts.gTTS.__init__", fake_gtts_init)
        monkeypatch.setattr("gtts.gTTS.save", fake_save)

        resp = client.post(
            "/api/tts", json={"text": "hello", "language": language, "voice": voice_id}
        )
        assert resp.status_code == 200
        assert seen["lang"] == expected_lang_code


class TestGenerateSpeech:
    def test_successful_generation(self, client, monkeypatch):
        _fake_gtts_save(monkeypatch)
        resp = client.post(
            "/api/tts",
            json={"text": "Hello, this is a test.", "language": "en", "voice": "en-us-standard"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["audio_url"].startswith("/audio/")
        assert data["audio_url"].endswith(".mp3")

    def test_generated_audio_is_servable(self, client, monkeypatch):
        _fake_gtts_save(monkeypatch, payload=b"1234567890")
        gen = client.post(
            "/api/tts",
            json={"text": "Serve me", "language": "en", "voice": "en-us-standard"},
        )
        audio_url = gen.get_json()["audio_url"]
        resp = client.get(audio_url)
        assert resp.status_code == 200
        assert resp.content_type == "audio/mpeg"
        assert resp.data == b"1234567890"

    def test_empty_text_rejected(self, client):
        resp = client.post(
            "/api/tts", json={"text": "   ", "language": "en", "voice": "en-us-standard"}
        )
        assert resp.status_code == 400
        assert "empty" in resp.get_json()["error"].lower()

    def test_missing_text_field_rejected(self, client):
        resp = client.post("/api/tts", json={"language": "en", "voice": "en-us-standard"})
        assert resp.status_code == 400

    def test_text_over_limit_rejected(self, client):
        long_text = "a" * 1000
        resp = client.post(
            "/api/tts",
            json={"text": long_text, "language": "en", "voice": "en-us-standard"},
        )
        assert resp.status_code == 400
        assert "maximum" in resp.get_json()["error"].lower()

    def test_invalid_language_rejected(self, client):
        resp = client.post(
            "/api/tts", json={"text": "hello", "language": "zz", "voice": "en-us-standard"}
        )
        assert resp.status_code == 400

    def test_voice_not_belonging_to_language_rejected(self, client):
        resp = client.post(
            "/api/tts", json={"text": "hello", "language": "en", "voice": "hi-standard"}
        )
        assert resp.status_code == 400
        assert "not available" in resp.get_json()["error"].lower()

    def test_non_json_body_rejected(self, client):
        resp = client.post("/api/tts", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_provider_failure_returns_503(self, client, monkeypatch):
        def raise_network_error(self, fp):
            raise ConnectionError("simulated network failure")

        monkeypatch.setattr("gtts.gTTS.save", raise_network_error)
        resp = client.post(
            "/api/tts", json={"text": "hello", "language": "en", "voice": "en-us-standard"}
        )
        assert resp.status_code == 503
        assert resp.get_json()["success"] is False


class TestAutoTranslate:
    def test_translate_before_speech(self, client, monkeypatch):
        _fake_gtts_save(monkeypatch)
        _fake_translate(monkeypatch)
        resp = client.post(
            "/api/tts",
            json={
                "text": "hello",
                "language": "hi",
                "voice": "hi-standard",
                "auto_translate": True,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["original_text"] == "hello"
        assert data["translated_text"] == "TRANSLATED: hello"
        assert data["audio_url"].startswith("/audio/")

    def test_auto_translate_defaults_to_false(self, client, monkeypatch):
        _fake_gtts_save(monkeypatch)
        resp = client.post(
            "/api/tts",
            json={"text": "hello", "language": "en", "voice": "en-us-standard"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "translated_text" not in data

    def test_auto_translate_must_be_boolean(self, client):
        resp = client.post(
            "/api/tts",
            json={
                "text": "hello",
                "language": "en",
                "voice": "en-us-standard",
                "auto_translate": "yes",
            },
        )
        assert resp.status_code == 400

    def test_translation_failure_returns_503(self, client, monkeypatch):
        """Both providers failing (not just Google) is what should 503."""

        def raise_error(self, text):
            raise ConnectionError("simulated network failure")

        monkeypatch.setattr("deep_translator.GoogleTranslator.translate", raise_error)
        monkeypatch.setattr("deep_translator.MyMemoryTranslator.translate", raise_error)
        resp = client.post(
            "/api/tts",
            json={
                "text": "hello",
                "language": "hi",
                "voice": "hi-standard",
                "auto_translate": True,
            },
        )
        assert resp.status_code == 503
        assert resp.get_json()["success"] is False

    def test_translate_falls_back_to_mymemory_when_google_fails(self, client, monkeypatch):
        """A Google-only failure (e.g. its rate limit) should not surface as
        an error to the user — the request should quietly succeed via the
        MyMemory fallback instead."""

        def raise_rate_limit(self, text):
            raise Exception("You made too many requests to the server")

        _fake_gtts_save(monkeypatch)
        monkeypatch.setattr("deep_translator.GoogleTranslator.translate", raise_rate_limit)
        _fake_mymemory_translate(monkeypatch)

        resp = client.post(
            "/api/tts",
            json={
                "text": "hello",
                "language": "hi",
                "voice": "hi-standard",
                "auto_translate": True,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["translated_text"] == "MYMEMORY: hello"

    def test_mymemory_fallback_uses_english_not_auto_as_source(self, client, monkeypatch):
        """Regression test: MyMemory's API doesn't support 'auto' as a
        source language and silently returns an error message as if it
        were the translation instead of raising. The fallback must send a
        real source language (English), never 'auto', and must treat an
        error-shaped response as a failure rather than real output."""
        seen_sources = []

        def raise_rate_limit(self, text):
            raise Exception("You made too many requests to the server")

        def fake_mymemory_translate(self, text):
            seen_sources.append(self._source)
            return "MYMEMORY: " + text

        _fake_gtts_save(monkeypatch)
        monkeypatch.setattr("deep_translator.GoogleTranslator.translate", raise_rate_limit)
        monkeypatch.setattr("deep_translator.MyMemoryTranslator.translate", fake_mymemory_translate)

        resp = client.post(
            "/api/tts",
            json={
                "text": "hi how are you",
                "language": "ml",
                "voice": "ml-standard",
                "auto_translate": True,
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["translated_text"] == "MYMEMORY: hi how are you"
        assert seen_sources == ["en-GB"]
        assert "auto" not in seen_sources

    def test_mymemory_error_shaped_response_is_treated_as_failure(self, client, monkeypatch):
        def raise_rate_limit(self, text):
            raise Exception("You made too many requests to the server")

        def fake_mymemory_error_text(self, text):
            return "'AUTO' IS AN INVALID SOURCE LANGUAGE, SELECT A SUPPORTED LANGUAGE"

        _fake_gtts_save(monkeypatch)
        monkeypatch.setattr("deep_translator.GoogleTranslator.translate", raise_rate_limit)
        monkeypatch.setattr(
            "deep_translator.MyMemoryTranslator.translate", fake_mymemory_error_text
        )

        resp = client.post(
            "/api/tts",
            json={
                "text": "hello",
                "language": "ml",
                "voice": "ml-standard",
                "auto_translate": True,
            },
        )
        assert resp.status_code == 503
        assert resp.get_json()["success"] is False

    def test_voices_response_includes_max_text_length(self, client):
        resp = client.get("/api/voices")
        data = resp.get_json()
        assert "max_text_length" in data
        assert isinstance(data["max_text_length"], int)


class TestErrorHandlers:
    def test_unknown_route_returns_404_json(self, client):
        resp = client.get("/api/does-not-exist")
        assert resp.status_code == 404
        assert resp.get_json()["success"] is False

    def test_wrong_method_returns_405(self, client):
        resp = client.delete("/api/tts")
        assert resp.status_code == 405


class TestPathTraversalSafety:
    def test_audio_route_rejects_traversal(self, client):
        resp = client.get("/audio/..%2f..%2fapp.py")
        assert resp.status_code == 404