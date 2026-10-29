# web-voice-kit

> **Unofficial community project. Not affiliated with, endorsed by, or supported by Gnani AI.**
> It calls Gnani's public speech APIs with your own API key. "Gnani" and "Vachana" belong to their owners.
> Built by one person (Kaushik M) for the Great Indian AI Internship Challenge.

A small kit for putting Gnani's speech APIs into a **web app without exposing your API key**, plus a working
example on top of it: a **Tamil-English payment-promise voice agent** that listens to a caller, extracts the amount
and the day, reads them back, and only accepts a clear "yes".

It is a demo and a learning project. **No audio is recorded, nothing is paid, no real payment system is involved.**

## What is in here

| Part | Where | What it does |
|---|---|---|
| Server proxy | `server/` | FastAPI. Keeps the key on the server. `/tts` (text to speech), `/stt` (live speech-to-text relay), per-address limits |
| Browser kit | `client/` | React + TypeScript hooks `useGnaniSTT` and `useGnaniTTS`, plus an AudioWorklet that converts any microphone to the 16 kHz frames Gnani needs |
| Payment-promise agent | `examples/voice-agent/`, `server/agent.py`, `client/src/callFlow.ts` | Pulls amount and day out of Tanglish speech and runs the confirm-by-read-back conversation |
| Eval | `eval/` | 23 labelled clips of my own voice, a scorer, edge-case tests |

## Quick start

You need Python 3.10+, Node.js 22, and your own Gnani API key.

```
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r server/requirements.txt
```

Copy `.env.example` to `.env` and put your key after `GNANI_API_KEY=`. **Never commit `.env`.**

Terminal 1 (server):

```
uvicorn server.main:app --reload
```

Terminal 2 (page):

```
cd client
npm install
npm run dev
```

Open http://localhost:5173. Use **Start listening** for a plain live transcript, or **Start call** for the
payment-promise demo. In the demo, wait until the pill says "listening - speak now" before you talk (see Limits).

Optional, one process only: `cd client && npm run build`, then run the server; it serves the built page at
http://localhost:8000.

On Windows PowerShell, if scripts are blocked, use `npm.cmd` instead of `npm` and call `.venv\Scripts\python.exe` directly.

## How a call works

```
 caller's voice -> [browser: mic -> AudioWorklet -> 16 kHz frames]
                         |  WebSocket /stt          (your server adds the API key)
                         v
                  [your server]  --WebSocket-->  Gnani realtime STT  -> Tamil-script transcript
                         ^
 transcript ---> POST /agent/turn  (extract amount + day, merge with what is known, decide what to ask)
                         |
 agent text  ---> POST /tts ---> Gnani Timbre v3.0 ---> audio played in the browser
                         |
 caller says yes / no ---> POST /agent/confirm ---> yes: done.  no (+ correction): fix and read back again.
```

The microphone is switched off while the agent speaks, so it never hears itself.

### Safety rules of the agent (all covered by tests)

- It always reads the amount and the date back and waits for an answer.
- **Silence is never consent.** No answer after the read-back means it asks again once, then ends the call.
- An answer with both a yes-word and a no-word is "unclear". It asks again and never assumes yes.
- A correction ("no, five thousand") is read back again before it is accepted.
- If the speech-to-text looks like it lost the number ("thousand rupees" with nothing before it), it does not guess 1,000. It asks "How much exactly?".
- A day it is not sure about is never stored. It asks instead.
- "Next Friday" means that weekday in the next Monday-Sunday week. That is a convention, so the date is read back ("Friday, 06 November") for the caller to correct.

## Why the key stays on the server

Gnani's realtime speech-to-text takes its settings (key, language, sample rate) as **headers on the WebSocket
upgrade request**, and browsers cannot set custom headers on a WebSocket. So a server has to open that connection.
That also means the key never ships in the page, where anyone could read it. The server also limits how many
sessions and calls one address can make, so a public demo cannot burn your credits.

## What I measured (read this before quoting any number)

Real findings from speaking Tamil-English to Gnani's `ta-IN` realtime STT with `format=transcribe`:

- `ta-IN` handled my mixed speech far better than `en-IN`, which produced nonsense such as "hamein".
- English words come out **in Tamil script, spelled differently each time** (thousand appeared as `தௌசண்ட்`).
- Numbers come back as a **mix of digits and words**: "two thousand five hundred" became `டூ தௌசண்ட் 500`. A regex that takes the first digits reads 500 instead of 2,500.
- Words get **dropped or garbled**: "three" before "thousand" was lost twice, and a weekday was missing entirely once.

Extractor results on my 23 development clips (one speaker, one microphone, my own voice, made-up sentences):

| | Correct | Asked again | Confidently wrong |
|---|---|---|---|
| Amount | 22 / 23 | 1 | 0 |
| Day | 21 / 23 | 2 | 0 |
| A plain "first digits" regex, for comparison | 5 / 23 | 15 found no digits at all | 3 |
| Yes / no after the read-back | 12 / 12 | - | 0 |

**These are development-set numbers, not an accuracy claim.** I wrote and tuned the extractor while looking at these
same clips, so they are optimistic. Reproduce them with `python eval/score.py`. A fresh set that the code never saw is
planned in `eval/HOLDOUT.md`, and that result will be added here, whatever it shows.

### Holdout result (14 fresh sentences, frozen code at tag `extractor-v1`)

| What | Correct | Asked again | Confidently wrong |
|---|---|---|---|
| Amount | 12 / 14 | 1 | 1 (75,000 heard as 5,000) |
| Day | 11 / 14 | 2 | 1 (spoken "next Monday" came back as "Monday") |
| Both right | **9 / 14 (64%)** | | |

So the dev-set numbers above were optimistic. Five clips failed: three because words the extractor did not know
(seventy, "one" before thousand, the ordinals fifth and twentieth), one because the transcript had no "next", and one
because an unknown word before "five thousand" silently turned 75,000 into 5,000. Only 14 clips, one speaker, one
microphone: treat 64% as a rough indication, not a measured accuracy. The fixes are commit `1d62d48` (tag `extractor-v2`): new
words (seventy, one, fifth, twentieth) and a guard that makes the agent ask when an unknown word sits right before a
number. The missing "next" cannot be fixed in code; the spoken read-back ("Monday, 02 November") is what catches it.
Scores of `extractor-v2` on the first holdout are not a fair test, because I fixed it while looking at those clips.
Eighty and ninety spellings are unverified guesses (eighty, "எயிட்டி", did come out right in the second set).

### Second holdout result (14 new sentences, frozen code at tag `extractor-v2`)

| What | Correct | Asked again | Confidently wrong |
|---|---|---|---|
| Amount | 12 / 14 | 1 | 1 (fifty thousand heard as 100,000) |
| Day | 12 / 14 | 2 | 0 |
| Both right | **11 / 14 (79%)** | | |

Failures: the transcript said "fifty fifty thousand" (the two fifties were added up to 100,000), the spelling
"இன்னிக்கு" for today and the ordinal "டென்த்" (tenth) were not known. 14 clips, one speaker: treat 64% then 79% as
"somewhere between two-thirds and four-fifths on my own voice", not as an accuracy figure. Anything fixed after this
point is untested until a third fresh set is recorded.

After that result I fixed the three causes (commit following `e98cba8`, tag `extractor-v3`): two spoken tens in a row
now make the agent ask, "இன்னிக்கு" is today, "டென்த்" is tenth. The three sets now score 20/23, 13/14 and 13/14, but
two of them were fixed while looking at them, so those numbers are not evidence. The honest figures are the ones above:
9/14 then 11/14 on unseen sentences.

## Limits and things not done

- One speaker, one microphone, one room. Nothing here says it works for other voices, accents or phones.
- Only 16 kHz microphone audio is sent. 8 kHz phone-call audio is **not evaluated**.
- Only Tamil-English (and a little plain English) was tested. Hindi and the other Gnani languages were not.
- The agent **speaks English**. A Tamil read-back is future work.
- If you speak before the page says "listening - speak now", the first word can be lost. This is my best explanation for
  the dropped "three", supported by one test so far, not proven.
- The agent cannot be interrupted while it speaks.
- Limits are in memory and per client address: fine for a demo, not for production. Behind a reverse proxy every user may look like one address.
- There is no login. Do not expose this server publicly with a key that has real credits.
- The number words the extractor knows are the forms seen in my recordings plus a few common ones (see `examples/voice-agent/extract.py`). Other spellings will fall through to "ask again".

## Privacy

Audio and transcripts are not stored or logged by the server. The eval panel in the demo saves text labels in your own
browser only. Use your own voice and made-up amounts: no real phone, account, Aadhaar or PAN numbers.

## Tests

```
python eval/test_extract.py        # edge cases (Friday vs forty, month end vs Monday, ...)
python eval/score.py               # scores the extractor on eval/eval-set.json
cd client && npm test              # resampler + conversation flow (12 checks)
cd client && npm run typecheck
```

Against the real Gnani servers: `python server/test_tts.py` and `python server/test_stt.py out.wav ta-IN`
(needs your key; uses a little credit).

## HTTP / WebSocket surface

- `POST /tts` `{text (max 500 chars), voice, language, model}` -> `audio/wav`
- `WS /stt?lang=ta-IN&rate=16000&fmt=transcribe` -> send 1,024-byte PCM frames at real-time speed, receive JSON transcripts
- `POST /agent/turn` `{text, amount?, day?, today?}` -> merged amount/day, the next thing to say, whether it still needs clarification
- `POST /agent/confirm` `{text}` -> `{intent: yes | no | unclear, amount?, day?}`
- `GET /health`

## License

MIT. See `LICENSE`.
