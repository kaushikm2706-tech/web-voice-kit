"""Score the extractor on the labelled clips.   Run: python eval/score.py [path-to-eval-set.json]
Counts each clip as one of: correct, ASKS (agent would ask the caller again: safe), WRONG (confident and wrong: dangerous)."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Tamil text on Windows consoles
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples", "voice-agent"))
import extract as ex

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "eval-set.json")
all_rows = json.load(open(path, encoding="utf-8"))
data = [r for r in all_rows if r["note"] not in ("yes", "no")]        # amount/day clips
yn = [r for r in all_rows if r["note"] in ("yes", "no")]               # confirmation clips

def key(d):
    return None if not d else (d["kind"], d.get("weekday"), d.get("date"), d.get("modifier"))

def naive_amount(text):          # baseline: first run of digits, like a plain regex would
    import re
    m = re.search(r"\d+", ex.tokens(text) and " ".join(ex.tokens(text)))
    return int(m.group()) if m else None

rows, fails = [], []
for r in data:
    p = ex.parse(r["transcript"])
    gold_day = ex.parse(r["expectedDay"])["day"]           # same parser reads the English label
    a_ok = p["amount"] == r["expectedAmount"]
    a_none = p["amount"] is None
    day_low = bool(p["day"] and p["day"]["conf"] == "low")
    d_ok = (not day_low) and key(p["day"]) == key(gold_day)
    d_ask = p["day"] is None or day_low
    rows.append(dict(lang=r["lang"], note=r["note"], a_ok=a_ok, a_ask=a_none, d_ok=d_ok, d_ask=d_ask,
                     naive=naive_amount(r["transcript"]) == r["expectedAmount"]))
    if not (a_ok and d_ok):
        fails.append((r, p, a_ok, d_ok))

def pct(n, t): return f"{n}/{t} = {100*n/t:.0f}%"
N = len(rows)
print(f"\n{N} clips from {os.path.basename(path)}\n")
print("AMOUNT  correct :", pct(sum(x['a_ok'] for x in rows), N))
print("        asks    :", sum(x['a_ask'] for x in rows))
print("        WRONG   :", sum((not x['a_ok']) and (not x['a_ask']) for x in rows))
print("DAY     correct :", pct(sum(x['d_ok'] for x in rows), N))
print("        asks    :", sum((not x['d_ok']) and x['d_ask'] for x in rows))
print("        WRONG   :", sum((not x['d_ok']) and (not x['d_ask']) for x in rows))
both = sum(x['a_ok'] and x['d_ok'] for x in rows)
print("BOTH correct    :", pct(both, N))
print("\nbaseline 'first digits in the transcript' amount accuracy:", pct(sum(x['naive'] for x in rows), N))
for lang in sorted({x['lang'] for x in rows}):
    sub = [x for x in rows if x['lang'] == lang]
    print(f"  {lang}: both correct {pct(sum(x['a_ok'] and x['d_ok'] for x in sub), len(sub))}")
noisy = [x for x in rows if x['note'] in ('fan on', 'tv on')]
if noisy:
    print(f"  noisy ({len(noisy)} clips): both correct {pct(sum(x['a_ok'] and x['d_ok'] for x in noisy), len(noisy))}")
if fails:
    print("\nFAILURES")
    for r, p, a_ok, d_ok in fails:
        print(f"- {r['transcript']}\n    wanted {r['expectedAmount']} / {r['expectedDay']!r}   got {p['amount']} / {p['day']}   "
              f"[amount {'ok' if a_ok else 'BAD'}, day {'ok' if d_ok else 'BAD'}]")
if yn:
    print("\nCONFIRMATION (yes/no after the read-back)")
    bad = 0
    for r in yn:
        got = ex.confirm_intent(r["transcript"])["intent"]
        ok = got == r["note"]
        bad += (not ok)
        if not ok:
            print(f"- {r['transcript']}  wanted {r['note']}  got {got}")
    print(f"  correct: {pct(len(yn)-bad, len(yn))}   (an 'unclear' makes the agent ask again)")
import os as _os
if "holdout" in _os.path.basename(sys.argv[1] if len(sys.argv) > 1 else ""):
    print("\nNOTE: a holdout file is fair only for the code tag it was scored on (holdout-set: extractor-v1 9/14; holdout2-set: extractor-v2 11/14). Code changed after,")
    print("so today's score on it is NOT a fair test. A new fresh set is needed for any claim about the current code.")
else:
    print("\nNOTE: the extractor was tuned while looking at these same clips, so these numbers are optimistic.")
