"""Tamil-English payment-promise extractor (web-voice-kit example, UNOFFICIAL, not affiliated with Gnani AI).

Input : one transcript line from Gnani STT (Tamil mode), e.g. "நெக்ஸ்ட் வீக் டூ தௌசண்ட் 500 ரூபீஸ் பே பண்ணுற"
Output: amount (int rupees or None), day (dict or None), and a read-back sentence to confirm.

Why it is built this way (all seen in real recordings, see eval/):
  * Gnani writes English words in Tamil script ("தௌசண்ட்" = thousand) with spelling that varies run to run,
    so words are matched on a consonant skeleton, not on exact spelling.
  * It mixes digits and words ("டூ தௌசண்ட் 500" = 2500, "10 தௌசண்ட்" = 10000, "700 ஃபிஃப்டி" = 750),
    so digits and words are merged into ONE number, never "first digit wins".
  * Some words are dropped or garbled ("Monday" missing entirely), so a missing or doubtful part is
    reported as None / low confidence and the agent must ASK, never guess.
"""
import calendar
import datetime as dt
import re
import unicodedata

# ---------------------------------------------------------------- text helpers
_CONS = {"க": "k", "ங": "n", "ச": "s", "ஞ": "n", "ட": "t", "ண": "n", "த": "t", "ந": "n", "ப": "p",
         "ம": "m", "ய": "y", "ர": "r", "ல": "l", "வ": "v", "ழ": "l", "ள": "l", "ற": "r", "ன": "n",
         "ஜ": "j", "ஷ": "s", "ஸ": "s", "ஹ": "h"}


def skel(word: str) -> str:
    """Tamil-script word -> consonant skeleton (vowels, pulli dropped, repeats collapsed)."""
    out = []
    for ch in unicodedata.normalize("NFC", word):
        c = _CONS.get(ch)
        if c and (not out or out[-1] != c):
            out.append(c)
    return "".join(out)


def tokens(text: str):
    t = unicodedata.normalize("NFC", text).lower().replace("₹", " ₹ ")
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)          # 1,000 -> 1000
    t = re.sub(r"[.,!?;:()\"']", " ", t)
    return t.split()


# ---------------------------------------------------------------- number words
# ("n", value) adds, ("m", value) multiplies the running part.
_SKEL_NUM = {}
def _add(variants, kind, value):
    for v in variants.split():
        _SKEL_NUM[skel(v)] = (kind, value)

_add("வன்", "n", 1)
_add("த்ரீ திரீ", "n", 3)
_add("ஃபோர் போர்", "n", 4)
_add("ஃபைவ் பைவ்", "n", 5)
_add("சிக்ஸ்", "n", 6)
_add("செவன்", "n", 7)
_add("எயிட் எய்ட்", "n", 8)
_add("டென்", "n", 10)
_add("ட்வெல்வ் டுவெல் டுவெல்வ் ட்வெல்", "n", 12)
_add("ஃபிஃப்டீன் ஃபிஃப்ட்டின் ஃபிப்டீன்", "n", 15)
_add("ட்வென்டி", "n", 20)
_add("தர்ட்டி", "n", 30)
_add("ஃபோர்ட்டி", "n", 40)
_add("ஃபிஃப்டி ஃபிப்டி", "n", 50)
_add("சிக்ஸ்டி", "n", 60)
_add("ஹண்ட்ரட் ஹன்ட்ரட் ஹண்ட்ரெட்", "m", 100)
_add("தௌசண்ட் தவுசண்ட் தௌசன்ட் தவுசன்ட்", "m", 1000)
_add("லாக் லட்சம்", "m", 100000)
_add("ஆயிரம்", "m", 1000)

# short words, matched exactly on the raw token (their skeleton is too short to be safe)
_RAW_NUM = {"டூ": ("n", 2), "டு": ("n", 2), "நைன்": ("n", 9), "எட்": ("n", 8), "ஏட்": ("n", 8),
            "ஒரு": ("n", 1), "நூறு": ("m", 100), "ஐநூறு": ("n", 500), "இரண்டாயிரம்": ("n", 2000)}

_EN_NUM = {"one": ("n", 1), "two": ("n", 2), "three": ("n", 3), "four": ("n", 4), "five": ("n", 5),
           "six": ("n", 6), "seven": ("n", 7), "eight": ("n", 8), "nine": ("n", 9), "ten": ("n", 10),
           "twelve": ("n", 12), "fifteen": ("n", 15), "twenty": ("n", 20), "thirty": ("n", 30),
           "forty": ("n", 40), "fifty": ("n", 50), "sixty": ("n", 60), "hundred": ("m", 100),
           "thousand": ("m", 1000), "lakh": ("m", 100000)}

# ---------------------------------------------------------------- days
_MON, _TUE, _WED, _THU, _FRI, _SAT, _SUN = range(7)
_TAMIL_DAYS = [("ஞாயிறு", _SUN), ("திங்கள்", _MON), ("செவ்வாய்", _TUE), ("புதன்", _WED),
               ("வியாழன்", _THU), ("வெள்ளி", _FRI), ("சனி", _SAT)]            # raw prefixes
_PHON_DAYS = [("snt", _SUN), ("mnt", _MON), ("tyst", _TUE), ("vtnst", _WED), ("vnst", _WED),
              ("trst", _THU), ("pryt", _FRI), ("strt", _SAT)]                  # skeleton prefixes
_EN_DAY_WORDS = {}
for _names, _wd in (("monday mon", _MON), ("tuesday tue tues", _TUE), ("wednesday wed", _WED),
                    ("thursday thu thur thurs", _THU), ("friday fri", _FRI), ("saturday sat", _SAT),
                    ("sunday sun", _SUN)):
    for _n in _names.split():
        _EN_DAY_WORDS[_n] = _wd
_ORDINAL_SKEL = {"ptnt": 15, "tnt": 10, "ptt": 5}   # fifteenth, tenth (only forms seen so far)


def _is_latin(t):
    return t.isascii() and t.isalpha()


def _day_at(toks, i):
    """Return (day_dict, tokens_consumed) if a day expression starts at toks[i], else None."""
    t = toks[i]
    nxt = toks[i + 1] if i + 1 < len(toks) else ""
    hi = "high"
    m = re.fullmatch(r"(\d{1,2})(st|nd|rd|th|ஆம்|ம்)", t)
    if m:
        return {"kind": "date", "date": int(m.group(1)), "conf": hi}, 1
    # month end: raw check FIRST (month "மந்த்" has the same skeleton as Monday "மண்டே")
    if t.startswith(("மந்த்", "மன்த்")) or t == "month":
        if nxt.startswith(("எண்ட", "end", "முடிவு", "கடைசி")):
            return {"kind": "end_of_month", "conf": hi}, 2
        return None
    if t == "end" and nxt == "of" and i + 2 < len(toks) and toks[i + 2].startswith(("month", "the")):
        return {"kind": "end_of_month", "conf": hi}, 3
    if t == "day" and nxt == "after":
        for j in range(i + 2, min(i + 4, len(toks))):
            if toks[j].startswith("tom"):
                return {"kind": "day_after", "conf": hi}, j - i + 1
    if t.startswith("நாளை") and nxt.startswith("மறுநாள்"):
        return {"kind": "day_after", "conf": hi}, 2
    if t.startswith("நாளை") or (_is_latin(t) and t.startswith("tom")):
        return {"kind": "tomorrow", "conf": hi}, 1
    if t.startswith(("இன்று", "இன்றை", "இன்னை")) or t == "today":
        return {"kind": "today", "conf": hi}, 1
    # Friday ("ஃப்ரைடே") and forty ("ஃபோர்ட்டி") share the skeleton "prt": tell them apart on the raw spelling.
    if t.startswith(("ஃப்ரை", "ப்ரை", "ஃப்ரெ", "ப்ரெ")):
        return {"kind": "weekday", "weekday": _FRI, "conf": hi}, 1
    for pre, wd in _TAMIL_DAYS:
        if t.startswith(pre):
            return {"kind": "weekday", "weekday": wd, "conf": hi}, 1
    if t in _EN_DAY_WORDS:
        return {"kind": "weekday", "weekday": _EN_DAY_WORDS[t], "conf": hi}, 1
    if not _is_latin(t):
        s = skel(t)
        if s and not t.startswith("ரூ"):
            if s.startswith("ptr") and nxt and "tmr" in skel(nxt):       # "ஆஃப்டர் டுமாரோ"
                return {"kind": "day_after", "conf": hi}, 2
            if s in _ORDINAL_SKEL or any(s.startswith(k) for k in _ORDINAL_SKEL if len(k) >= 4):
                for k, v in _ORDINAL_SKEL.items():
                    if s.startswith(k):
                        return {"kind": "date", "date": v, "conf": hi}, 1
            for pre, wd in _PHON_DAYS:
                if s.startswith(pre):
                    return {"kind": "weekday", "weekday": wd, "conf": hi}, 1
            if s == "tmr" or s.startswith("tmr"):
                return {"kind": "tomorrow", "conf": hi}, 1
            if "tmr" in s:                       # garbled, e.g. "ஏ கட்டுமாரோ": could be tomorrow OR day-after
                return {"kind": "tomorrow", "conf": "low"}, 1
            if s == "vk":
                return {"kind": "week", "conf": hi}, 1
    if t == "week":
        return {"kind": "week", "conf": hi}, 1
    return None


def _modifier(toks, i):
    for j in (i - 1, i - 2):
        if j < 0:
            continue
        t = toks[j]
        if t == "next" or t.startswith("அடுத்த") or skel(t).startswith("nkst"):
            return "next"
        if t == "this" or t.startswith("இந்த"):
            return "this"
    return None


# ---------------------------------------------------------------- number parsing
def _num_token(t):
    if re.fullmatch(r"\d+", t):
        return ("n", int(t))
    if t in _EN_NUM:
        return _EN_NUM[t]
    for raw in ("ஐநூறு", "இரண்டாயிரம்"):
        if t.startswith(raw):
            return _RAW_NUM[raw]
    if t in _RAW_NUM:
        return _RAW_NUM[t]
    s = skel(t)
    if len(s) >= 2 and s in _SKEL_NUM:
        return _SKEL_NUM[s]
    return None


def _run_value(run):
    """['n',2],['m',1000],['n',500] -> 2500. Digits and words merge into one number."""
    total, cur = 0, 0
    for kind, v in run:
        if kind == "n":
            cur += v
        else:
            total += (cur or 1) * v if v >= 1000 else 0
            if v >= 1000:
                cur = 0
            else:
                cur = (cur or 1) * v
    return total + cur


def _is_rupee(t):
    return t == "₹" or t.startswith(("ரூ", "ரு", "rupee", "rs", "inr"))


def parse(text: str):
    toks = tokens(text)
    day, day_idx = None, None
    events = []          # ("num", kind, value, idx) | ("rupee", idx)
    i = 0
    while i < len(toks):
        d = _day_at(toks, i)
        if d:
            if day is None:
                day, day_idx = d[0], i
                day["modifier"] = _modifier(toks, i)
            i += d[1]
            continue
        if _is_rupee(toks[i]):
            events.append(("rupee", i))
        else:
            nt = _num_token(toks[i])
            if nt:
                events.append(("num", nt[0], nt[1], i))
        i += 1

    # group consecutive number tokens into runs
    runs, cur = [], []
    for e in events:
        if e[0] == "num" and (not cur or e[3] == cur[-1][3] + 1):
            cur.append(e)
        else:
            if cur:
                runs.append(cur)
            cur = [e] if e[0] == "num" else []
    if cur:
        runs.append(cur)
    runs = [r for r in runs if not (len(r) == 1 and r[0][2] == 1)]      # lone "ஒரு"/"one" is not an amount
    rupee_idx = [e[1] for e in events if e[0] == "rupee"]

    def near(run):
        return min((min(abs(r - run[0][3] + 1), abs(r - run[-1][3] - 1)) for r in rupee_idx), default=99)

    amount = None
    if runs:
        best = min(runs, key=lambda r: (near(r), runs.index(r)))
        v = _run_value([(e[1], e[2]) for e in best])
        amount = v if v > 0 else None
    return {"amount": amount, "day": day}


# ---------------------------------------------------------------- dates + read-back
def resolve(day, today: dt.date):
    """Turn a day dict into a calendar date, or None when it cannot be decided."""
    if not day:
        return None
    k = day["kind"]
    if k == "today":
        return today
    if k == "tomorrow":
        return today + dt.timedelta(days=1)
    if k == "day_after":
        return today + dt.timedelta(days=2)
    if k == "weekday":
        wd, mod = day["weekday"], day.get("modifier")
        if mod == "next":                      # the same weekday in NEXT calendar week (Mon-Sun)
            return today + dt.timedelta(days=7 - today.weekday() + wd)
        ahead = (wd - today.weekday()) % 7
        if mod == "this":
            return today + dt.timedelta(days=ahead)
        return today + dt.timedelta(days=ahead or 7)
    if k == "date":
        d = day["date"]
        y, m = today.year, today.month
        if d < today.day:
            m, y = (1, y + 1) if m == 12 else (m + 1, y)
        return dt.date(y, m, d) if d <= calendar.monthrange(y, m)[1] else None
    if k == "end_of_month":
        return dt.date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    return None                                # "next week" alone: which day?


def inr(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
    return f"₹{head},{tail}"


def extract(text: str, today: dt.date):
    """Full result for the agent: what was heard, what to say back, and what to ask."""
    p = parse(text)
    amount, day = p["amount"], p["day"]
    when = resolve(day, today)
    low = bool(day and day["conf"] == "low")
    if amount is None and (day is None or low):
        ask = "I did not catch the amount or the day. Could you say both again?"
    elif amount is None:
        ask = "How much will you pay?"
    elif day is None or low:
        ask = f"I heard {inr(amount)}. On which day will you pay?"
    elif when is None:
        ask = f"I heard {inr(amount)} next week. Which day next week?"
    else:
        ask = f"I heard {inr(amount)} on {when.strftime('%A, %d %B')}. Is that right?"
    return {"amount": amount, "day": day, "date": when, "confirm_prompt": ask,
            "needs_clarification": amount is None or day is None or low or when is None}
