"""Edge cases found by reading results, not only by the score.   Run: python eval/test_extract.py"""
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
print("ALL PASS" if all(r) else "SOME FAILED"); sys.exit(0 if all(r) else 1)
