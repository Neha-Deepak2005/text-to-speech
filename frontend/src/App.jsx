import { useEffect, useState } from "react";
import TextInput from "./components/TextInput.jsx";
import LanguageSelector from "./components/LanguageSelector.jsx";
import VoiceSelector from "./components/VoiceSelector.jsx";
import TranslateToggle from "./components/TranslateToggle.jsx";
import GenerateButton from "./components/GenerateButton.jsx";
import AudioPlayer from "./components/AudioPlayer.jsx";
import DownloadButton from "./components/DownloadButton.jsx";
import ErrorMessage from "./components/ErrorMessage.jsx";
import { getVoices, generateSpeech, toAbsoluteAudioUrl } from "./api.js";

// Fallback used only until the backend's real limit has loaded, so the
// text area has a sane cap before /api/voices responds.
const FALLBACK_MAX_LENGTH = 500;

export default function App() {
  const [languages, setLanguages] = useState({});
  const [languageGroups, setLanguageGroups] = useState({});
  const [voicesByLanguage, setVoicesByLanguage] = useState({});
  const [maxLength, setMaxLength] = useState(FALLBACK_MAX_LENGTH);
  const [language, setLanguage] = useState("");
  const [voice, setVoice] = useState("");
  const [text, setText] = useState("");
  const [autoTranslate, setAutoTranslate] = useState(false);
  const [translatedText, setTranslatedText] = useState(null);
  const [translationWarning, setTranslationWarning] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  // Load available languages/voices (and the backend's real text limit) on
  // first render, so the frontend never drifts out of sync with the API.
  useEffect(() => {
    let cancelled = false;

    async function loadVoices() {
      try {
        const data = await getVoices();
        if (cancelled) return;
        setLanguages(data.languages);
        setLanguageGroups(data.language_groups || {});
        setVoicesByLanguage(data.voices);
        if (typeof data.max_text_length === "number") {
          setMaxLength(data.max_text_length);
        }
        const firstLang = Object.keys(data.languages)[0];
        setLanguage(firstLang);
        setVoice(data.voices[firstLang]?.[0]?.id || "");
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoadingVoices(false);
      }
    }

    loadVoices();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleLanguageChange(newLang) {
    setLanguage(newLang);
    const firstVoice = voicesByLanguage[newLang]?.[0]?.id || "";
    setVoice(firstVoice);
  }

  async function handleGenerate() {
    setError(null);
    setTranslatedText(null);
    setTranslationWarning(null);

    const trimmed = text.trim();
    if (trimmed.length === 0) {
      setError("Please enter some text before generating speech.");
      return;
    }
    if (trimmed.length > maxLength) {
      setError(`Text exceeds the maximum allowed length of ${maxLength} characters.`);
      return;
    }
    if (!language || !voice) {
      setError("Please select a language and voice.");
      return;
    }

    setGenerating(true);
    setAudioUrl(null);
    try {
      const data = await generateSpeech({ text: trimmed, language, voice, autoTranslate });
      setAudioUrl(toAbsoluteAudioUrl(data.audio_url));
      if (data.translated_text) {
        setTranslatedText(data.translated_text);
      }
      if (data.translation_warning) {
        setTranslationWarning(data.translation_warning);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  const currentVoices = voicesByLanguage[language] || [];
  const isBackendReady = !loadingVoices && Object.keys(languages).length > 0;
  const controlsDisabled = !isBackendReady || generating;

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto w-full max-w-xl">
        <header className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Text to Speech</h1>
          <p className="mt-1 text-sm text-slate-500">
            Convert written text into natural-sounding speech.
          </p>
        </header>

        <div className="space-y-5 rounded-2xl bg-white p-6 shadow-md">
          <ErrorMessage message={error} onDismiss={() => setError(null)} />

          <TextInput
            text={text}
            onChange={setText}
            maxLength={maxLength}
            disabled={controlsDisabled}
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <LanguageSelector
              languages={languages}
              groups={languageGroups}
              value={language}
              onChange={handleLanguageChange}
              disabled={controlsDisabled}
            />
            <VoiceSelector
              voices={currentVoices}
              value={voice}
              onChange={setVoice}
              disabled={controlsDisabled}
            />
          </div>

          <TranslateToggle
            checked={autoTranslate}
            onChange={setAutoTranslate}
            disabled={controlsDisabled}
          />

          <GenerateButton
            onClick={handleGenerate}
            loading={generating}
            disabled={!isBackendReady}
          />

          {translatedText && (
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
              <span className="font-medium">Translated text: </span>
              {translatedText}
            </div>
          )}

          {translationWarning && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <span className="font-medium">Note: </span>
              {translationWarning}
            </div>
          )}

          {audioUrl && (
            <div className="space-y-3 border-t border-slate-200 pt-4">
              <AudioPlayer src={audioUrl} />
              <DownloadButton src={audioUrl} filename="speech.mp3" />
            </div>
          )}
        </div>

        <footer className="mt-6 text-center text-xs text-slate-400">
          Powered by React + Flask + gTTS
        </footer>
      </div>
    </div>
  );
}