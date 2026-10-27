"""Calls the local /tts endpoint and saves out.wav. Run the server first."""
import sys
import httpx

URL = "http://localhost:8000/tts"
body = {"text": "Hello, this is a test."}

try:
    r = httpx.post(URL, json=body, timeout=60)
except httpx.HTTPError as e:
    sys.exit(f"Could not reach {URL}. Is the server running? ({e})")

if r.status_code == 200:
    with open("out.wav", "wb") as f:
        f.write(r.content)
    print(f"OK: saved out.wav ({len(r.content)} bytes). Double-click it to listen.")
else:
    print("FAILED:", r.status_code, r.text)
    sys.exit(1)
