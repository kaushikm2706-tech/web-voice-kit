"""Edge cases found by reading results, not only by the score.   Run: python eval/test_extract.py"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Tamil text on Windows consoles
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples", "voice-agent"))
import extract as ex

def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name); return ok

r = []
r.append(check("'வேற day' garble is NOT forty", ex.confirm_intent("தப்பு பேரடே")["amount"] is None))
r.append(check("real forty still works", ex.parse("ஃபோர்ட்டி தௌசண்ட் ருபீஸ்")["amount"] == 40000))
r.append(check("Friday is not forty", ex.parse("ஃப்ரைடேக்கு ஃபைவ் தௌசண்ட்")["day"]["weekday"] == 4))
r.append(check("digits + words merge: 2 thousand 500", ex.parse("டூ தௌசண்ட் 500")["amount"] == 2500))
r.append(check("digit + thousand: 10 thousand", ex.parse("10 தௌசண்ட் ருபீஸ்")["amount"] == 10000))
r.append(check("700 + fifty", ex.parse("700 ஃபிஃப்டி ருபீஸ்")["amount"] == 750))
r.append(check("month end is not Monday", ex.parse("மந்த் எண்டில்")["day"]["kind"] == "end_of_month"))
r.append(check("fifteenth is a date, not an amount", ex.parse("ஃபிஃப்டீன்த்துக்கு டுவெல் தௌசண்ட்")["amount"] == 12000))
r.append(check("yes and no together -> unclear", ex.confirm_intent("ஆமாம் இல்லை")["intent"] == "unclear"))
r.append(check("silence/noise -> unclear", ex.confirm_intent("ஹலோ")["intent"] == "unclear"))
r.append(check("no + correction carries amount", ex.confirm_intent("இல்லை த்ரீ தௌசண்ட்")["amount"] == 3000))
r.append(check("Friday spelling variant ஃபிரைடே", ex.parse("ஃபிரைடே")["day"]["weekday"] == 4))
import datetime as _dt
_t = _dt.date(2026, 10, 27)
_a = ex.turn("700 ஃபிஃப்டி ருபீஸ்", _t)
r.append(check("turn: missing day -> asks for the day", _a["needs_clarification"] and "which day" in _a["confirm_prompt"].lower()))
_b = ex.turn("வெள்ளிக்கிழமை", _t, _a["amount"], _a["day"])
r.append(check("turn: day answer merges with earlier amount", _b["amount"] == 750 and str(_b["date"]) == "2026-10-30"))
_c = ex.turn("இல்லை த்ரீ தௌசண்ட்", _t, _b["amount"], _b["day"])
r.append(check("turn: correction replaces amount, keeps day", _c["amount"] == 3000 and str(_c["date"]) == "2026-10-30"))
_d = ex.turn("நான் ஏ கட்டுமாரோ ஃபிஃப்டி தௌசண்ட்", _t)
r.append(check("turn: garbled day is never stored, agent asks", _d["day"] is None and _d["needs_clarification"]))
_e = ex.turn("தௌசண்ட் ரூபீஸ்", _t)          # real live-call case: "three thousand" came back as just "thousand"
r.append(check("bare 'thousand' is NOT guessed as 1,000: agent asks", _e["amount"] is None and _e["needs_clarification"] and "how much exactly" in _e["confirm_prompt"].lower()))
_f = ex.turn("தௌசண்ட் ரூபீஸ்", _t, 2500, {"kind": "tomorrow", "conf": "high", "modifier": None})
r.append(check("bare 'thousand' also drops a stale earlier amount", _f["amount"] is None))
r.append(check("'three thousand' still fine", ex.parse("த்ரீ தௌசண்ட் ருபீஸ்")["amount"] == 3000))
r.append(check("Tamil 'ஆயிரம்' alone is a normal 1000", ex.parse("ஆயிரம் ரூபாய்")["amount"] == 1000))
# --- found by the holdout set (eval/holdout-set.json) ---
_t2 = _dt.date(2026, 10, 28)
_h = ex.parse("மந்த் எண்டில் செவன்ட்டி ஃபைவ் தௌசண்ட் ருபீஸ் தரேன்")
r.append(check("holdout: seventy five thousand = 75000, not 5000", _h["amount"] == 75000))
r.append(check("holdout: unknown word before a number run -> ask, never a silent wrong amount",
               ex.parse("மந்த் எண்டில் சிக்ஸ்டீன் தௌசண்ட் ருபீஸ்")["amount"] is None))
r.append(check("holdout: 'ஒன்' is one: 1200", ex.parse("தர்ஸ்டேக்கு ஒன் தௌசண்ட் டூ ஹண்ட்ரட் ருபீஸ்")["amount"] == 1200))
r.append(check("holdout: fifth is the 5th", ex.parse("ஃபிஃப்த்துக்கு டுவெண்ட்டி தௌசண்ட்")["day"] == {"kind": "date", "date": 5, "conf": "high", "modifier": None}))
r.append(check("holdout: twentieth is the 20th", ex.parse("டுவெண்ட்டியத்துக்கு தேர்ட்டி தௌசண்ட்")["day"]["date"] == 20))
r.append(check("fifteen is still an amount, fifth did not steal it", ex.parse("ஃபிஃப்டீன் ஹண்ட்ரட் ருபீஸ்")["amount"] == 1500))
r.append(check("eight hundred is not eighty", ex.parse("எயிட் ஹண்ட்ரட் ருபீஸ்")["amount"] == 800))
# the new guard must not fire on ordinary sentences
for _txt, _amt in (("நான் நாளைக்கு சிக்ஸ் தௌசண்ட் ஃபைவ் ஹண்ட்ரட் ருபீஸ் கட்டுவேன்", 6500),
                   ("நான் சண்டேக்கு ₹1,000 தரேன்", 1000),
                   ("i will pay ₹5,000 on friday", 5000),
                   ("இன்னைக்கு நைன் ஹண்ட்ரட் ருபீஸ் தரேன்", 900),
                   ("நெக்ஸ்ட் வீக் டூ தௌசண்ட் 500 ரூபீஸ் பே பண்ணுற", 2500)):
    r.append(check("guard has no false alarm: " + _txt[:28], ex.parse(_txt)["amount"] == _amt))
print("ALL PASS" if all(r) else "SOME FAILED"); sys.exit(0 if all(r) else 1)
