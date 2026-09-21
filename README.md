# Text-to-Speech Application

A full-stack web application that converts written text into natural-sounding
speech, built with **React** on the frontend and **Python (Flask)** on the
backend. Users can enter text, choose a language and voice, generate audio,
play it back, and download it as an MP3.

This implementation targets **Level 1 (Basic)** of the project plan: text
input, language/voice selection, speech generation, playback and download,
with full input validation and error handling.

---

## 1. Tech Stack

| Layer            | Technology                                   |
|-------------------|-----------------------------------------------|
| Frontend          | React 18, Vite, Tailwind CSS, Axios           |
| Backend           | Python 3, Flask, Flask-CORS, Flask-Limiter    |
| Text-to-Speech    | [gTTS](https://gtts.readthedocs.io/) (Google Translate TTS — free, no API key) |
| Translation       | [deep-translator](https://github.com/nidhaloff/deep-translator) (free Google Translate, no API key) |
| Testing           | Pytest (backend), Postman collection (API), GitHub Actions CI |

### Why gTTS instead of a paid cloud TTS API?

The project plan lists Google Cloud TTS, Azure Speech, Amazon Polly and
ElevenLabs as possible providers. All of them are genuinely good options,
but they require creating a cloud account, enabling billing, and generating
a credential/API key before you can make a single request — that setup can
easily eat a day or two on its own.

**gTTS** wraps the same free endpoint Google Translate's website uses to
read text aloud. It needs **no signup and no API key**, so the app works
immediately after `pip install`. The trade-off: gTTS gives you **one
synthetic voice per language**, not true male/female voices. To still make
"voice selection" meaningful, each language offers a few real, functional
presets built from gTTS's supported parameters:

- **Accent** (English, Spanish, French have region variants: US/UK/India/
  Australia, Spain/US, France/Canada) via the `tld` parameter.
- **Speaking pace** ("Standard" vs. "Slow & Clear") via the `slow` parameter.

This is called out here explicitly so it's easy to explain in a viva: the
app does not claim "male voice" / "female voice" because gTTS cannot
actually deliver that — everything it offers is real and testable.

If you later want true multi-voice (male/female, WaveNet-quality) audio,
swap the implementation in `backend/services/tts_service.py` for Google
Cloud TTS, Azure, Polly or ElevenLabs — the rest of the app (routes,
validation, frontend) does not need to change, since they all speak the
same `generate_speech(text, language, voice) -> filename` contract.

> **Note on this environment:** gTTS needs outbound internet access to
> `translate.google.com` to generate audio. It was implemented and unit
> tested here with the network call mocked (the sandbox this was built in
> has restricted outbound access), so **the first thing to do on your own
> machine is the "Smoke test" below** to confirm live generation works
> before you rely on it for your submission.

### Auto-translate (optional add-on, beyond the original plan)

By itself, gTTS does not translate — the Language selector only controls
*pronunciation*. If you type English but pick Hindi, gTTS will try to read
those English letters using Hindi phonetics, which sounds broken, not
Hindi.

To fix that, the app has an opt-in **"Translate my text into the selected
language before generating speech"** checkbox. When checked, the backend
translates your input into the target language (via `deep-translator`,
same no-API-key approach as gTTS) *before* handing it to gTTS, and returns
both the original and translated text so you can see exactly what was
spoken. It's off by default, so the app's default behavior still matches
the plan exactly — this is a clearly-labeled bonus feature you can mention
as an enhancement in your submission/demo.

Backend contract: `POST /api/tts` accepts an optional `auto_translate:
boolean` field (default `false`). When `true`, the success response
additionally includes `original_text` and `translated_text`.

**Two-provider fallback:** Google's free translation endpoint enforces a
hard rate limit (5 requests/sec, 200k/day) *per source IP* — and on shared
hosting (like Render's free tier), that IP is shared across many unrelated
apps, so the limit can be hit even when this app alone is well within it.
To make the feature reliable on a deployed instance, `translation_service.py`
tries Google first and, if that fails for any reason, automatically retries
with **MyMemoryTranslator** (also free, no API key) before returning an
error — so a rate limit on one provider doesn't take the feature down.

One caveat: MyMemory's API (unlike Google's) can't auto-detect the source
language, so the fallback assumes English input, matching this app's
documented use case ("type in English, hear it in another language"). If
Google is rate-limited *and* you typed non-English text, the MyMemory
fallback may mistranslate — a rare double-edge case, and still strictly
better than the request failing outright.

**Graceful degradation:** both providers are free/no-key services with
their own outside rate limits, and on shared hosting it's possible (if
uncommon) for both to be limited at once. Rather than blocking speech
generation entirely in that case, `POST /api/tts` falls back to speaking
the *original* text and returns a non-fatal `translation_warning` field
instead of an error — so the core TTS feature (the actual plan
requirement) never fails just because the bonus translate feature is
temporarily unavailable. The frontend shows this as an amber notice next
to the audio player, distinct from a real error.

### Supported Languages

24 languages, each verified against both gTTS's and deep-translator's
actual supported-language lists (not assumed) — 11 Indian and 13 others,
matching the plan's example list plus a broader set on request. Each gets
a "Standard" and "Slow & Clear" voice preset at minimum:

| Indian Languages | Other Languages |
|---|---|
| Hindi, Gujarati, Marathi, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Urdu, Nepali | English*, Spanish, French†, German, Italian, Portuguese†, Russian, Japanese, Korean, Chinese†, Arabic, Dutch, Turkish |

\* English additionally offers 4 real accent presets (US / UK / India /
Australia) via gTTS's `tld` parameter — the one case gTTS documents as a
genuine accent difference, not a guess.

† French, Portuguese and Chinese additionally offer a real regional
variant gTTS exposes as a distinct language code (not just a `tld` guess):
French (Canada), Portuguese (Portugal), and Chinese (Taiwan) alongside the
default France/Brazil/Simplified voice.

The frontend groups the Language dropdown into "Indian Languages" and
"Other Languages" `<optgroup>`s automatically, using a `language_groups`
field the backend adds to `GET /api/voices` — see Section 5.

Adding another language later is a backend-only change: add one entry to
`LANGUAGES` and at least one `Voice(...)` to `VOICES` in
`backend/services/tts_service.py` (and its group in `LANGUAGE_GROUPS`) —
first check the code is in both `gtts.lang.tts_langs()` and
`GoogleTranslator().get_supported_languages(as_dict=True)`, the way every
language above was verified, since a code gTTS accepts isn't guaranteed to
be one deep-translator also accepts (this is why "zh" needed a small
override — see `translation_service.py`).

---

## 2. Project Structure

```
text-to-speech/
│
├── .github/workflows/            # CI: backend tests + frontend build
│   ├── backend-tests.yml
│   └── frontend-build.yml
│
├── frontend/                    # React + Vite + Tailwind app
│   ├── src/
│   │   ├── components/
│   │   │   ├── TextInput.jsx
│   │   │   ├── LanguageSelector.jsx
│   │   │   ├── VoiceSelector.jsx
│   │   │   ├── TranslateToggle.jsx
│   │   │   ├── GenerateButton.jsx
│   │   │   ├── AudioPlayer.jsx
│   │   │   ├── DownloadButton.jsx
│   │   │   └── ErrorMessage.jsx
│   │   ├── App.jsx
│   │   ├── api.js               # Axios client + error handling
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .env.example
│
├── backend/                     # Flask app
│   ├── app.py                   # App factory, CORS, error handlers, /audio route
│   ├── config.py                # Env-driven configuration
│   ├── extensions.py            # Shared Flask-Limiter instance
│   ├── routes/
│   │   └── tts_routes.py        # /api/tts, /api/voices, /api/health
│   ├── services/
│   │   ├── tts_service.py       # gTTS integration, languages/voices, cleanup
│   │   └── translation_service.py  # Optional auto-translate (deep-translator)
│   ├── utils/
│   │   └── validators.py        # Request validation
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_tts_routes.py   # 21 passing pytest cases
│   ├── generated_audio/         # Generated MP3s (git-ignored, auto-cleaned)
│   ├── requirements.txt
│   └── .env.example
│
├── postman_collection.json      # Import into Postman to test the API
└── README.md
```

---

## 3. Prerequisites

- **Python 3.9+** and `pip`
- **Node.js 18+** and `npm`
- Internet access (gTTS calls Google's translate endpoint at generation time)

---

## 4. Setup & Running Locally

### 4.1 Backend (Flask)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # defaults are fine for local dev

python app.py                     # runs on http://localhost:5000
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### 4.2 Frontend (React)

In a **second terminal**:

```bash
cd frontend
npm install

cp .env.example .env              # points VITE_API_BASE_URL at the backend

npm run dev                       # runs on http://localhost:5173
```

Open **http://localhost:5173** in your browser. Type some text, pick a
language and voice, and click **Generate Speech**.

### 4.3 Smoke test (do this first!)

Confirm gTTS can actually reach Google from your machine before you build
on top of it:

```bash
cd backend
source venv/bin/activate
python3 -c "from gtts import gTTS; gTTS(text='Hello world', lang='en').save('test.mp3'); print('OK, size:', __import__('os').path.getsize('test.mp3'), 'bytes')"
```

If this prints a non-zero byte size, live speech generation works. If it
raises a connection error, you're on a network that blocks Google Translate
(a restrictive campus/office firewall, for example) — try a different
network, or switch the provider as described above.

---

## 5. API Reference

Base URL: `http://localhost:5000`

### `GET /api/health`
Health check.

```json
{ "status": "ok" }
```

### `GET /api/voices`
Returns supported languages and voice presets. Optional `?language=en` to
filter to one language.

```json
{
  "success": true,
  "languages": { "en": "English", "hi": "Hindi", "...": "... (24 total)" },
  "voices": {
    "en": [
      { "id": "en-us-standard", "label": "English (US) – Standard", "tld": "com", "slow": false, "lang_code": null },
      { "id": "en-us-slow", "label": "English (US) – Slow & Clear", "tld": "com", "slow": true, "lang_code": null }
    ]
  },
  "language_groups": {
    "Indian Languages": ["hi", "gu", "mr", "..."],
    "Other Languages": ["en", "es", "fr", "..."]
  },
  "max_text_length": 500
}
```

### `POST /api/tts`
Generates speech audio. Optionally translates the text first.

Request:
```json
{
  "text": "Welcome to our application.",
  "language": "en",
  "voice": "en-us-standard",
  "auto_translate": false
}
```
`auto_translate` is optional (defaults to `false`). Set it to `true` to
translate `text` into `language` before speech is generated — see
"Auto-translate" above.

Success response (`200`), `auto_translate: false`:
```json
{ "success": true, "audio_url": "/audio/3f2a1b9c....mp3" }
```

Success response (`200`), `auto_translate: true`:
```json
{
  "success": true,
  "audio_url": "/audio/3f2a1b9c....mp3",
  "original_text": "Welcome to our application.",
  "translated_text": "आपके एप्लिकेशन में आपका स्वागत है।"
}
```
`audio_url` is relative to the backend base URL — fetch the full audio at
`http://localhost:5000/audio/<file>.mp3`.

Success response (`200`), `auto_translate: true` but both translation
providers were unavailable — speech is generated from the original text
instead, and `translation_warning` explains why (see "Graceful
degradation" above):
```json
{
  "success": true,
  "audio_url": "/audio/3f2a1b9c....mp3",
  "translation_warning": "Translation is temporarily unavailable, so the original text was used instead. (...)"
}
```

Error response (`400` / `429` / `503`):
```json
{ "success": false, "error": "Text must not be empty." }
```

### `GET /audio/<filename>`
Serves a previously generated MP3 file (`Content-Type: audio/mpeg`). Files
older than `AUDIO_RETENTION_MINUTES` (default 30) are deleted automatically
the next time `/api/tts` is called, per the plan's security guidance not to
store generated audio permanently.

### HTTP status codes used
| Code | Meaning                         | When |
|------|----------------------------------|------|
| 200  | Success                          | Valid request, audio generated / data returned |
| 400  | Invalid request                  | Empty text, text too long, invalid language/voice, malformed JSON |
| 404  | Not found                        | Unknown route or missing audio file |
| 405  | Method not allowed               | Wrong HTTP verb on a route |
| 429  | Too many requests                | Rate limit exceeded on `/api/tts` (default: 10/minute/IP) |
| 500  | Internal server error            | Unexpected server-side exception |
| 503  | External service unavailable     | gTTS itself couldn't be reached (translation failures no longer 503 — see "Graceful degradation" above) |

---

## 6. Testing

### 6.1 Backend unit/integration tests (pytest)

```bash
cd backend
source venv/bin/activate
pytest -v
```

44 tests cover: health check, listing/filtering voices, successful
generation, serving the generated file, empty/over-limit/missing text,
invalid language, voice-doesn't-belong-to-language, non-JSON body,
simulated provider failure (→ 503), auto-translate (success, default-off,
invalid type, fallback from Google to MyMemory on failure, MyMemory's
"auto"-source quirk, and both providers failing gracefully falling back to
the original text rather than erroring), that all 11 Indian + 13 other
languages are present and each generates speech, that the four real
regional-accent voices (French Canada, Portuguese Portugal, Chinese
Simplified/Taiwan) pass the *correct* gTTS language code rather than
silently reusing the parent language, 404/405 error handling, and a
path-traversal safety check on `/audio/<filename>`. The gTTS and
translation network calls are mocked so the suite runs fully offline and
deterministically.

A GitHub Actions workflow (`.github/workflows/backend-tests.yml`) runs
this same suite on every push/PR that touches `backend/`, and a second
workflow (`frontend-build.yml`) runs `npm run build` on every push/PR that
touches `frontend/` — once you push to GitHub, both show up as checks on
your repo, which is worth pointing out in your submission as evidence of
automated testing.

### 6.2 API testing with Postman

Import `postman_collection.json` into Postman. It includes requests (each
with an assertion) for all three endpoints, plus the error cases: empty
text, over-length text, invalid language, voice/language mismatch, and
wrong `Content-Type`. Start the backend first (`python app.py`), then
**Run collection**.

### 6.3 Manual frontend checklist

- [ ] Empty text → clicking Generate shows an inline error, no request sent
- [ ] Text near/over the character limit shows the counter in red
- [ ] Changing language resets the voice list to that language's options
- [ ] Generate shows a loading state, then reveals the audio player
- [ ] Audio plays, pauses, seeks, and volume can be adjusted (native controls)
- [ ] Download saves an `.mp3` file that plays correctly
- [ ] Stopping the backend and clicking Generate shows a network-error message
- [ ] Checking "Translate my text..." + English input + Hindi language produces
      Hindi audio and shows the translated text box above the player

---

## 7. Environment Variables

### `backend/.env`
| Variable | Default | Purpose |
|---|---|---|
| `FLASK_DEBUG` | `True` | Enables Flask's debug/reload mode (turn off in production) |
| `PORT` | `5000` | Backend port |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Comma-separated allowed CORS origin(s) |
| `MAX_TEXT_LENGTH` | `500` | Max characters accepted per request |
| `AUDIO_RETENTION_MINUTES` | `30` | How long generated files are kept |
| `RATE_LIMIT_TTS` | `10 per minute` | Rate limit on `POST /api/tts` per IP |

### `frontend/.env`
| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:5000` | Backend base URL the frontend calls |

`.env` files are git-ignored on both sides — never commit real credentials.
If you switch to a paid TTS provider, its API key goes in `backend/.env`
only, and is read on the server; it must never be sent to or stored in the
React app.

---

## 8. Security Notes (implemented)

- API credentials (if you add a paid provider) live only in `backend/.env`,
  never in frontend code — see Section 7.
- All input is validated server-side (`backend/utils/validators.py`) —
  the frontend never trusted to enforce limits alone.
- `POST /api/tts` is rate-limited (`Flask-Limiter`) to prevent abuse.
- Maximum text length is enforced (`MAX_TEXT_LENGTH`).
- CORS is restricted to the configured frontend origin(s), not `*`.
- Generated audio files are named with random UUIDs (not user input) and
  served via `send_from_directory`, which rejects path traversal.
- Generated audio is periodically cleaned up rather than stored forever.

For production you would additionally want: HTTPS termination, a
production WSGI server (gunicorn/uwsgi) instead of Flask's dev server, and
a persistent rate-limit backend (Redis) instead of in-memory.

---

## 9. Deployment (live)

- **Frontend:** deployed on **Vercel** — https://text-to-speech-ten-sand.vercel.app
  (built from `frontend/` via `npm run build`, with `VITE_API_BASE_URL` set
  to the backend URL below as an environment variable).
- **Backend:** deployed on **Render** — https://text-to-speech-backend-6lcn.onrender.com
  (via the `render.yaml` Blueprint at the repo root, running
  `gunicorn app:app`), with `FRONTEND_ORIGIN` set to the Vercel URL above.

Render's free tier spins the backend down after inactivity, so the first
request after a while can take 30-50 seconds to respond while it wakes up.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Frontend shows "Could not reach the server" | Backend isn't running, or `VITE_API_BASE_URL` is wrong |
| `gtts.tts.gTTSError: Failed to connect` | No internet access to Google, or it's blocked on your network |
| CORS error in browser console | `FRONTEND_ORIGIN` in `backend/.env` doesn't match the URL your frontend is actually served from |
| `429 Too many requests` | You hit the rate limit — wait a minute, or raise `RATE_LIMIT_TTS` in `backend/.env` |
| Audio won't download | Browser blocked the popup fallback — check console; the primary path uses a blob download and shouldn't need popups |

---

## 11. Deliverables Checklist (Section 24 of the plan)

- [x] Source code (this repository)
- [x] GitHub repository — https://github.com/Neha-Deepak2005/text-to-speech
- [x] README documentation (this file)
- [ ] Database schema — not applicable (Level 1 has no database)
- [x] API documentation (Section 5 above)
- [ ] UI screenshots — add after running the app
- [x] Deployment URL:
  - Frontend (live app): https://text-to-speech-ten-sand.vercel.app
  - Backend (API): https://text-to-speech-backend-6lcn.onrender.com
- [x] Postman collection (`postman_collection.json`)
- [ ] Project presentation
- [ ] Short project demonstration

> **Note on the backend URL:** it's hosted on Render's free tier, which
> spins down after periods of inactivity. The first request after a lull
> can take 30-50 seconds to wake it back up — if a demo/reviewer sees a
> slow first response, that's why; it's normal and not a bug.

---

## 12. Suggested Improvements

Grouped by how much time they cost, so you can pick based on how much
runway you have before the 20th.

### Quick (under ~30 minutes each) — worth doing regardless of time
- **Add a "Copy translated text" button** next to the translated-text box,
  for when someone wants the text without the audio.
- **Disable the browser spellcheck red squiggles** on the textarea
  (`spellCheck={false}`) since they're distracting on non-English text.
- **Show the detected source language** when auto-translating — swap
  `source="auto"` for `GoogleTranslator(...).source` after translating, or
  use `langdetect` — and display it next to the translated text (e.g.
  "Detected: English → Hindi").
- **Take the UI screenshots** of the live site and add them to your
  submission — the only checklist item in Section 11 still open besides
  the presentation/demo.

### Medium (an hour or two) — good polish before a demo
- **Cache identical requests.** If the same `(text, language, voice,
  auto_translate)` combination is requested twice, skip regenerating and
  reuse the existing file — saves API calls and feels instant on repeats.
  A simple in-memory dict keyed by a hash of the request is enough for a
  student project; note it resets on server restart.
- **Add WAV/OGG export.** The plan lists multiple formats as optional
  (Section 4.6); gTTS only produces MP3 natively, but you can convert with
  `pydub` (`ffmpeg` must be installed) and offer a format dropdown next to
  Download.
- **Persist the rate limiter to a real store.** Right now `Flask-Limiter`
  warns about using in-memory storage — fine for a demo, but swap in
  `flask-limiter[redis]` if you deploy somewhere with Redis available, so
  limits survive restarts and work correctly if you ever run more than one
  backend process.
- **Accessibility pass.** Add `aria-live="polite"` to `ErrorMessage` so
  screen readers announce errors, and `aria-busy` on the form while
  `generating` is true.

### Larger (Level 2 of the plan) — only if you have real time to spare
The plan's Level 2 adds user accounts, a database, speech history and
favorites:

1. Add a `database/` layer (SQLite is fastest to set up) with a `history`
   table (`text`, `language`, `voice`, `audio_url`, `created_at`).
2. Add `Flask-JWT-Extended` for auth and a `/api/auth/*` blueprint.
3. Save a history row inside `generate_speech()` after a successful call.
4. Add a "History" view in the frontend that lists and replays past audio.

This is intentionally left out of the delivered code so Level 1 (plus the
auto-translate add-on) stays small, fully tested, and reliably demoable by
your deadline. Attempting Level 2 with only a few days left risks ending
up with something half-working for the demo — better to have a smaller
app that works perfectly than a bigger one that doesn't.