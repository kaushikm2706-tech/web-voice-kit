"""Realtime speech-to-text relay. UNOFFICIAL: not affiliated with Gnani AI.

Why this exists: Gnani's realtime STT takes its settings (API key, language,
sample rate) as WebSocket upgrade HEADERS, and browsers cannot set custom
headers on a WebSocket. So the browser talks to THIS server, and this server
opens the real connection to Gnani and relays messages both ways.

Browser -> server:  ws://HOST/stt?lang=hi-IN&rate=16000&fmt=transcribe
  then send binary frames: PCM signed 16-bit little-endian, mono,
  EXACTLY 1024 bytes each, at real-time speed.
Server -> browser: Gnani's JSON messages, passed through unchanged
  (connected / processing / transcript / error).

Privacy: audio and transcripts are never logged or stored here.
"""
import asyncio
import json
import os
import time
from collections import defaultdict

import websockets
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketState

from .limits import RateLimiter

router = APIRouter()

# Overridable so tests can point at a fake server. Default is Gnani's endpoint.
UPSTREAM_URL = os.getenv("STT_UPSTREAM_URL", "wss://api.vachana.ai/stt/v3/stream")

LANGS = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"}
RATES = {8000, 16000}  # our design: browser sends 16 kHz; 8 kHz is for phone-quality tests
FORMATS = {"verbatim", "transcribe"}
FRAME_BYTES = 1024  # exactly 512 samples of 16-bit mono, per Gnani's docs
MAX_SESSION_S = 15 * 60  # Gnani's own cap is 15 minutes
BURST_FRAMES = 15  # headroom for network jitter before we call it "bursting"

MAX_CONCURRENT_PER_IP = int(os.getenv("STT_MAX_CONCURRENT", "2"))
sessions_limiter = RateLimiter(max_calls=int(os.getenv("STT_SESSIONS_PER_HOUR", "10")), window_s=3600)
_active = defaultdict(int)


async def _fail(ws: WebSocket, message: str) -> None:
    """Tell the browser what went wrong (same shape as Gnani's error), then close."""
    try:
        if ws.application_state == WebSocketState.CONNECTING:
            await ws.accept()
        await ws.send_text(json.dumps({"type": "error", "message": message}))
        await ws.close(code=1008)
    except Exception:
        pass


@router.websocket("/stt")
async def stt(ws: WebSocket, lang: str = "en-IN", rate: int = 16000, fmt: str = "verbatim"):
    # NOTE: we accept the browser's connection only AFTER Gnani is connected.
    # Otherwise the browser starts sending audio while we are still dialling Gnani,
    # the frames pile up, and they would look like a burst when we finally read them.
    ip = ws.client.host if ws.client else "unknown"

    if lang not in LANGS:
        return await _fail(ws, "Unsupported lang. Use one of: " + ", ".join(sorted(LANGS)))
    if rate not in RATES:
        return await _fail(ws, "Unsupported rate. Use 16000 or 8000.")
    if fmt not in FORMATS:
        return await _fail(ws, "Unsupported fmt. Use verbatim or transcribe.")

    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key:
        return await _fail(ws, "Server has no GNANI_API_KEY. Put it in the .env file and restart.")

    if _active[ip] >= MAX_CONCURRENT_PER_IP:
        return await _fail(ws, "Too many live sessions from this address. Close one and retry.")
    wait = sessions_limiter.check(ip)
    if wait:
        return await _fail(ws, f"Too many STT sessions from this address. Try again in {wait} seconds.")

    _active[ip] += 1
    up = None
    try:
        headers = {
            "x-api-key-id": key,
            "lang_code": lang,
            "x-sample-rate": str(rate),
            "x-format": fmt,
        }
        try:
            up = await websockets.connect(
                UPSTREAM_URL, additional_headers=headers, open_timeout=10, max_size=2**20
            )
        except websockets.exceptions.InvalidStatus as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (401, 403):
                return await _fail(ws, "Gnani refused the connection (check the API key and credits).")
            return await _fail(ws, f"Gnani refused the connection (HTTP {code}).")
        except Exception:
            return await _fail(ws, "Could not reach Gnani's realtime STT. Try again.")

        await ws.accept()
        frame_s = 512 / rate  # seconds of audio in one 1024-byte frame

        async def gnani_to_browser():
            async for msg in up:
                if isinstance(msg, str):
                    await ws.send_text(msg)

        async def browser_to_gnani():
            started = time.monotonic()
            frames = 0
            while True:
                m = await ws.receive()
                if m["type"] == "websocket.disconnect":
                    return
                data = m.get("bytes")
                if data is None:
                    continue  # ignore text frames from the browser for now
                if len(data) != FRAME_BYTES:
                    return await _fail(ws, f"Each audio frame must be exactly {FRAME_BYTES} bytes.")
                frames += 1
                allowed = (time.monotonic() - started) / frame_s + BURST_FRAMES
                if frames > allowed:
                    return await _fail(ws, "Audio is being sent faster than real time. Send one frame per 32 ms (16 kHz).")
                await up.send(data)

        tasks = [asyncio.create_task(gnani_to_browser()), asyncio.create_task(browser_to_gnani())]
        done, pending = await asyncio.wait(tasks, timeout=MAX_SESSION_S, return_when=asyncio.FIRST_COMPLETED)
        if not done:
            await _fail(ws, "Session reached the 15 minute limit. Reconnect to continue.")
        for t in pending:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        _active[ip] -= 1
        if up is not None:
            try:
                await up.close()
            except Exception:
                pass
        try:
            if ws.application_state != WebSocketState.CONNECTING:
                await ws.close()
        except Exception:
            pass
