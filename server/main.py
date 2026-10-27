"""web-voice-kit server. UNOFFICIAL: not affiliated with Gnani AI.

Holds the Gnani API key on the server so browsers never see it.
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Load .env BEFORE importing modules that read settings from the environment at import time.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .limits import RateLimiter
from .agent import router as agent_router
from .stt import router as stt_router


GNANI_BASE = "https://api.vachana.ai"
TTS_PATH = "/api/v1/tts/inference"

app = FastAPI(title="web-voice-kit (UNOFFICIAL, not affiliated with Gnani AI)")
app.include_router(stt_router)
app.include_router(agent_router)
limiter = RateLimiter(max_calls=int(os.getenv("TTS_CALLS_PER_HOUR", "20")), window_s=3600)


class TTSRequest(BaseModel):
    # Max 500 characters per call protects the free credits.
    text: str = Field(min_length=1, max_length=500)
    voice: str = "Shivani"
    language: str = "en-IN"
    model: str = "timbre-v3.0"


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/tts")
async def tts(req: TTSRequest, request: Request):
    wait = limiter.check(request.client.host if request.client else "unknown")
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"Too many TTS calls from this address. Try again in {wait} seconds.",
            headers={"Retry-After": str(wait)},
        )

    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Server has no GNANI_API_KEY. Put it in the .env file and restart.",
        )

    payload = {
        "text": req.text,
        "voice": req.voice,
        "model": req.model,
        "language": req.language,
        "audio_config": {
            "sample_rate": 24000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    headers = {"X-API-Key-ID": key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(GNANI_BASE + TTS_PATH, headers=headers, json=payload)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach Gnani. Check your internet and try again.")

    if r.status_code == 200:
        return Response(content=r.content, media_type="audio/wav")

    upstream = r.text[:300].replace(key, "***")
    if r.status_code == 400:
        msg = (
            "Gnani rejected the request (400). Voices are not shared between models: "
            "check that voice, model and language match. Gnani said: " + upstream
        )
    elif r.status_code == 403:
        msg = "Gnani says forbidden (403): check the API key, account status, or remaining credits."
    elif r.status_code == 429:
        msg = "Gnani rate limit hit (429). Wait a bit and retry."
    else:
        msg = f"Gnani returned {r.status_code}. Gnani said: " + upstream
    raise HTTPException(status_code=502 if r.status_code >= 500 else r.status_code, detail=msg)


# Optional: serve the built demo page from this same server (run `npm run build` inside client/ first).
# Registered last, so /tts, /stt, /agent and /health keep working.
_dist = Path(__file__).resolve().parent.parent / "client" / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_dist, html=True), name="demo")
