import axios from "axios";

// Base URL of the Flask backend. Configure via frontend/.env (VITE_API_BASE_URL).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

/**
 * Extract a user-friendly error message from any axios error, covering the
 * cases the project plan calls out: API failure, network failure, and
 * server errors with a JSON { error } body.
 */
function extractErrorMessage(error) {
  if (error.response) {
    // Server responded with a non-2xx status.
    const body = error.response.data;
    if (body && typeof body.error === "string") return body.error;
    if (error.response.status === 429) return "Too many requests. Please wait a moment and try again.";
    return `Server error (${error.response.status}). Please try again.`;
  }
  if (error.request) {
    // Request was made but no response was received.
    return "Could not reach the server. Check your connection and that the backend is running.";
  }
  return error.message || "An unexpected error occurred.";
}

export async function getHealth() {
  const res = await client.get("/api/health");
  return res.data;
}

export async function getVoices() {
  try {
    const res = await client.get("/api/voices");
    return res.data; // { success, languages, voices }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function generateSpeech({ text, language, voice, autoTranslate = false }) {
  try {
    const res = await client.post("/api/tts", {
      text,
      language,
      voice,
      auto_translate: autoTranslate,
    });
    return res.data; // { success, audio_url, original_text?, translated_text? }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

/** Turn a backend-relative audio_url ("/audio/xyz.mp3") into an absolute URL. */
export function toAbsoluteAudioUrl(audioUrl) {
  if (!audioUrl) return null;
  if (audioUrl.startsWith("http")) return audioUrl;
  return `${API_BASE_URL}${audioUrl}`;
}
