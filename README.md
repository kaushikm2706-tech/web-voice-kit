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
