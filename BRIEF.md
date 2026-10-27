# BRIEF.md: read this first, before writing any code

Working name: `web-voice-kit` (UNOFFICIAL community kit for Gnani AI's speech APIs; not affiliated with Gnani AI).
Owner: Kaushik M. Solo project for the Great Indian AI Internship Challenge. Final submission 10 Nov 2026, 11:59 PM IST.

## Goal
1. A small open-source kit that lets any web app talk to Gnani's speech APIs safely:
   - a FastAPI proxy that keeps the API key on the server
   - a React/TypeScript hook for the microphone and audio playback
   - ready-made VAD presets (clean mic vs 8 kHz phone audio)
2. A flagship demo on top of it: a payment-promise voice agent (customer says an amount and a date in Hinglish/Tanglish, the app extracts them live and reads them back).
3. A small eval pack: ~20 clips, accuracy at 16 kHz vs 8 kHz.

## Hard rules
- Never invent endpoints, parameters or message formats. If something is not in this file, fetch https://docs.gnani.ai/llms.txt, open the relevant .md page, and read it. If still unsure, write `TODO(verify)` in code and tell the user.
- The API key lives only in `.env` (`GNANI_API_KEY`). Never print it, log it, return it to the browser, or commit it. `.env` must be in `.gitignore`.
- Use synthetic or the owner's own voice data only. No real phone numbers, Aadhaar, PAN, bank details or recorded calls.
- Do not log audio or transcripts by default.
- Add per-IP and per-session limits so public use cannot burn the 5,000 free credits.
- Label anything simulated as simulated in the UI and README.
- Git: every commit must be authored by `Kaushik M`. No `Co-Authored-By` lines, no AI attribution anywhere (commits, README, headers). Run `git log --format='%an <%ae>'` after each commit and fix the author if it is wrong.

## VERIFIED API facts (from docs.gnani.ai, Oct 2026)
Base URL: `https://api.vachana.ai`. Auth header on every request: `X-API-Key-ID: <key>`.

### STT REST: `POST /stt/v3` (multipart/form-data)
- `audio_file` (WAV, MP3, OGG, FLAC, AAC, M4A; max 60 s, ideal 30 s)
- `language_code`: bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN
- `format`: `verbatim` (default) or `transcribe` (turns spoken numbers/currency/dates/phone/PIN into written form, e.g. "pay do lakh rupees by fifteenth march" -> "pay ₹2,00,000 by 15th March")
- `itn_native_numerals` (bool), `enable_substitution` + `substitution_map` (JSON, max 10 rules)
- `bias_list` (max 100 words, each ONE word, letters only) + `bias_score` in {0.0, 0.5, 1.0, 1.5, 2.0}. Use with `format=verbatim`. Invalid lists are silently ignored.
- Response: `{success, request_id, timestamp, transcript}`. Errors: 400, 403 (key/credits), 429 (rate limit), 500, 503.

### STT realtime: `wss://api.vachana.ai/stt/v3/stream`
- Settings go in WebSocket upgrade HEADERS: `x-api-key-id`, `lang_code`, `x-sample-rate` (8000/16000/44100/48000), `x-format`, optional VAD headers `x-vad-threshold` (default 0.7), `x-min-silence-ms` (500), `x-min-speech-ms` (100; 200 at 8 kHz), `x-min-segment-ms` (120), `x-max-speech-s`.
- Browsers CANNOT set these headers, so the server must open the Gnani connection and relay.
- Send binary PCM only: signed 16-bit little-endian, mono, EXACTLY 1,024 bytes per frame (512 samples), paced in real time (32 ms per frame at 16 kHz, 64 ms at 8 kHz). Do not burst.
- Server messages (JSON): `connected`, `processing`, `transcript` (`text`, `audio_duration_ms`, `segment_id`, `segment_index`, `latency`), `error`, `settings_updated`.
- Client control frame: `{"type":"update_settings", ...}` (substitution and bias only).
- Session cap: 15 minutes.
- Design choice (ours, not from docs): downsample browser audio to 16 kHz in an AudioWorklet and send 32 ms frames. `TODO(verify)` against the docs before relying on 44.1/48 kHz.

### TTS REST: `POST /api/v1/tts/inference` (JSON, returns binary audio)
Body: `text`, `voice`, `model`, `language`, `speed`, `audio_config {sample_rate, num_channels, sample_width, encoding:"linear_pcm", container:"wav"}`.
Streaming: `POST /api/v1/tts/sse`. Realtime: `wss://api.vachana.ai/api/v1/tts`.
- `model`: `timbre-v3.0` or `timbre-v2.5`. Voices are NOT interchangeable between models (400 error).
- Timbre v3.0 voices (each speaks all 10 languages): Shivani, Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika (female); Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad (male). `language` = a code above or `auto`.
- Timbre v2.5: 42 voices, one preferred language each; `speed` 0.85 to 1.15; Hinglish voice `Poorvi` with `language: "hi-en"`.
- Audio tags (v3.0 only), inline in `text`, case-sensitive: `<laugh> <giggle> <sigh> <exhales> <sniffles> <yawns> <coughs> <clears throat> <whispers> <shouting> <excited> <slow> <pauses>`. A tag applies from its position to the END of the input (or the next tag). There is no closing tag, so synthesize ONE SENTENCE PER CALL when mixing tones. Tags count as billable characters.

### SDKs
- `pip install gnani-vachana` (import `gnani`); `pip install pipecat-gnani` (Pipecat v1.5.0+). Pipecat is a stretch goal, not required.

## NOT yet verified. Test before building on them
- Whether `timbre-v3.0` works with the owner's contest key.
- Whether Tamil+English mixed speech transcribes acceptably with `ta-IN` vs `en-IN` (ITN examples in docs are Hindi/English only).
- Credit cost per STT/TTS call (owner will read the Pricing page).
- TTS WebSocket and SSE message formats (read docs.gnani.ai/api/TTS/tts-websocket.md before using).

## Contest rules to respect
Public demo video on LinkedIn and/or X with tag to Gnani AI, #GnaniAI and #GreatIndianAIInternshipChallenge; project must genuinely use Gnani models; no bought engagement, bots, engagement swaps or misleading demos.

## Repo layout
```
web-voice-kit/
  README.md        (unofficial disclaimer, 5-minute quickstart)
  BRIEF.md
  .env.example     GNANI_API_KEY=
  .gitignore       .env, node_modules, __pycache__, *.wav (except eval/clips)
  server/          FastAPI proxy (main.py, limits.py, requirements.txt)
  client/          React + TypeScript hook and player
  examples/voice-agent/   flagship demo
  eval/            clips + run_eval.py
```
