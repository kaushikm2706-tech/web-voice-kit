"""Round-trip test: send a WAV file to the local /stt relay in real time and print what comes back.

Usage (server must be running):
    python server\\test_stt.py out.wav
    python server\\test_stt.py out.wav hi-IN

Accepts any 16-bit WAV (mono or stereo, any sample rate); converts it to
16 kHz mono first. Use your own voice or synthetic audio only.
"""
import array
import asyncio
import json
import sys
import time
import wave

import websockets

FRAME = 1024  # bytes per frame = 512 samples at 16 kHz = 32 ms


def load_16k_mono(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2:
            sys.exit("Need a 16-bit WAV file.")
        ch, rate = w.getnchannels(), w.getframerate()
        raw = w.readframes(w.getnframes())
    s = array.array("h")
    s.frombytes(raw)
    if ch > 1:
        s = array.array("h", [sum(s[i:i + ch]) // ch for i in range(0, len(s) - ch + 1, ch)])
    if rate != 16000:  # simple linear resample, fine for a test
        n = int(len(s) * 16000 / rate)
        out = array.array("h")
        for i in range(n):
            pos = i * rate / 16000
            j = int(pos)
            frac = pos - j
            nxt = s[j + 1] if j + 1 < len(s) else s[j]
            out.append(int(s[j] * (1 - frac) + nxt * frac))
        s = out
    return s.tobytes()


async def main(path: str, lang: str):
    pcm = load_16k_mono(path)
    pcm += b"\x00" * (16000 * 2)  # 1 s of silence so the last words are finalised
    pcm += b"\x00" * (-len(pcm) % FRAME)
    url = f"ws://localhost:8000/stt?lang={lang}&rate=16000&fmt=transcribe"
    async with websockets.connect(url) as ws:
        async def reader():
            try:
                async for m in ws:
                    d = json.loads(m)
                    if d.get("type") == "transcript":
                        print("TRANSCRIPT:", d.get("text"), f"(latency {d.get('latency')} ms)")
                    else:
                        print(d.get("type"), d.get("message", ""))
            except websockets.ConnectionClosed:
                pass
        r = asyncio.create_task(reader())
        # Pace against the clock, not with a fixed sleep: on Windows a plain
        # asyncio.sleep(0.032) can wake early, and the relay rejects audio sent faster than real time.
        t0 = time.monotonic()
        try:
            for n, i in enumerate(range(0, len(pcm), FRAME)):
                target = t0 + n * 0.032
                delay = target - time.monotonic()
                if delay > 0.002:
                    await asyncio.sleep(delay - 0.002)
                while time.monotonic() < target:
                    await asyncio.sleep(0)
                await ws.send(pcm[i:i + FRAME])
            await asyncio.sleep(3)  # wait for the final transcript
        except websockets.ConnectionClosed:
            await asyncio.sleep(0.2)  # let the reader print the server's reason
            print("(connection closed by the server)")
        r.cancel()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python server\\test_stt.py yourfile.wav [lang]")
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "en-IN"))
