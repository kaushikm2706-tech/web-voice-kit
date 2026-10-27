# web-voice-kit

> UNOFFICIAL community kit. Not affiliated with Gnani AI. Built for the Great Indian AI Internship Challenge.

A small FastAPI server that keeps your Gnani API key off the browser, plus (coming next) a React mic hook and VAD presets.

## Run it (Windows)

Open a terminal in this folder, then:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r server\requirements.txt
uvicorn server.main:app --reload
```

Put your key after `GNANI_API_KEY=` in the `.env` file first (never share or commit it).

Open http://localhost:8000/docs, click `/tts`, `Try it out`, `Execute`.
Or, in a second terminal: `python server\test_tts.py` (saves `out.wav`).

## Limits
`/tts` accepts at most 500 characters and 20 calls per IP per hour (`TTS_CALLS_PER_HOUR` in `.env`) to protect free credits.

## Realtime speech-to-text (server relay)

Browsers cannot set the headers Gnani's realtime STT needs, so the server relays the connection:
`ws://localhost:8000/stt?lang=hi-IN&rate=16000&fmt=transcribe`. Send raw 16 kHz mono 16-bit PCM in
frames of exactly 1024 bytes, at real-time speed. Check it from the command line (server running):

    python server\test_stt.py out.wav

Limits: 2 live sessions per address, 10 sessions per hour, 15 minutes per session (Gnani's own cap).
Audio and transcripts are never logged or stored.

## Browser demo (React + TypeScript)

Needs Node.js 20.19 or newer (or 22.12 or newer). Run the server first (above), then in a second terminal:

    cd client
    npm install
    npm run dev

Open http://localhost:5173, press Start listening and allow the microphone. The kit is two hooks,
`useGnaniSTT` (mic to live transcript) and `useGnaniTTS` (text to speech), plus an AudioWorklet
(`client/public/pcm-worklet.js`) that converts any microphone sample rate to 16 kHz 1024-byte frames.
`npm test` checks the resampler.
