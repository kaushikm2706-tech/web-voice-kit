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
_add("செவன்ட்டி செவன்டி செவென்டி", "n", 70)   # seventy: seen in the holdout (செவன்ட்டி)
_add("ஹண்ட்ரட் ஹன்ட்ரட் ஹண்ட்ரெட்", "m", 100)
_add("தௌசண்ட் தவுசண்ட் தௌசன்ட் தவுசன்ட்", "m", 1000)
_add("லாக் லட்சம்", "m", 100000)
_add("ஆயிரம்", "m", 1000)

# short words, matched exactly on the raw token (their skeleton is too short to be safe)
# eighty / ninety share a skeleton with eight ("yt") or are short, so they are matched on the whole word.
# These spellings are my phonetic guesses, NOT seen in a recording (unverified).
_TENS_RAW = {"எய்ட்டி": 80, "எயிட்டி": 80, "ஏய்ட்டி": 80, "எய்டி": 80, "எயிடி": 80,
             "நைன்ட்டி": 90, "நைன்டி": 90, "நைண்ட்டி": 90}
_RAW_NUM = {"ஒன்": ("n", 1), "டூ": ("n", 2), "டு": ("n", 2), "நைன்": ("n", 9), "எட்": ("n", 8), "ஏட்": ("n", 8),
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
# fifth and twentieth, matched on the raw spelling (seen in the holdout: ஃபிஃப்த்துக்கு, டுவெண்ட்டியத்துக்கு).
# Must be checked before the number words: "ஃபிஃப்த்" is fifth, "ஃபிஃப்டீன்" is fifteen.
# thirtieth is my guess by analogy, not seen in a recording (unverified).
_ORDINAL_RAW = [(("டென்த்",), 10),
                (("ஃபிஃப்த்", "ஃபிப்த்", "பிஃப்த்", "பிப்த்"), 5),
                (("டுவெண்ட்டியத்", "டுவென்டியத்", "டுவெண்டியத்", "ட்வென்டியத்", "ட்வென்ட்டியத்"), 20),
                (("தர்ட்டியத்", "தேர்ட்டியத்"), 30)]


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
    if t.startswith(("இன்று", "இன்றை", "இன்னை", "இன்னி")) or t == "today":
        return {"kind": "today", "conf": hi}, 1
    for prefixes, dom in _ORDINAL_RAW:
        if t.startswith(prefixes):
            return {"kind": "date", "date": dom, "conf": hi}, 1
    # Friday ("ஃப்ரைடே") and forty ("ஃபோர்ட்டி") share the skeleton "prt": tell them apart on the raw spelling.
    if t.startswith(("ஃப்ரை", "ப்ரை", "ஃப்ரெ", "ப்ரெ", "ஃபிரை", "பிரை", "ஃபிரெ", "பிரெ")):
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
    if t in _TENS_RAW:
        return ("n", _TENS_RAW[t])
    if t in _RAW_NUM:
        return _RAW_NUM[t]
    s = skel(t)
    if s == "prt" and "ர்ட" not in t:      # "ஃபோர்ட்டி" (forty) has ர் + ட; "பேரடே" ("vera day") does not
        return None
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


# Tamil function words that may sit right before a number without being a missed number word.
_FUNCTION_PREFIX = ("நான்", "நாம்", "நாங்க", "எனக்கு", "அடுத்த", "இந்த", "ரூ", "ரு", "மொத்த", "கண்டிப்")


def _unknown_word_before(toks, start, consumed):
    """True when the word right before the number run looks like a number word we do not know.
    Real case: "செவன்ட்டி ஃபைவ் தௌசண்ட்" (seventy five thousand) was read as 5,000 because
    "செவன்ட்டி" was unknown and silently skipped. An unknown word there means: ask, never guess."""
    j = start - 1
    if j < 0 or j in consumed:
        return False
    t = toks[j]
    if not t or t[0].isascii() or t == "₹" or t.startswith(_FUNCTION_PREFIX) or _is_rupee(t):
        return False
    return len(skel(t)) >= 4


def parse(text: str):
    toks = tokens(text)
    day, day_idx = None, None
    consumed = set()
    events = []          # ("num", kind, value, idx) | ("rupee", idx)
    i = 0
    while i < len(toks):
        d = _day_at(toks, i)
        if d:
            if day is None:
                day, day_idx = d[0], i
                day["modifier"] = _modifier(toks, i)
            consumed.update(range(i, i + d[1]))
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

    amount, unsure = None, False
    # Two spoken tens/teens in a row ("fifty fifty thousand") is not a number anyone says: the speech-to-text
    # repeated or garbled a word, and adding them gave 100,000 instead of 50,000. Ask instead.
    # (A digit followed by a word, "700 fifty", IS normal Gnani output, so only word+word counts.)
    def _doubled(run):
        return any(a[1] == b[1] == "n" and a[2] >= 10 and b[2] >= 10
                   and not toks[a[3]].isdigit() and not toks[b[3]].isdigit()
                   for a, b in zip(run, run[1:]))
    if runs:
        best = min(runs, key=lambda r: (near(r), runs.index(r)))
        v = _run_value([(e[1], e[2]) for e in best])
        amount = v if v > 0 else None
        # "தௌசண்ட் ரூபீஸ்" with nothing before it: the speech-to-text may have DROPPED the number ("three").
        # Real case from a live call: "three thousand" came back as just "thousand". Do not guess 1,000: ask.
        first = best[0]
        if _doubled(best):
            amount, unsure = None, True
        elif first[1] == "m" and not toks[first[3]].startswith(("ஆயிரம்", "நூறு")):
            amount, unsure = None, True
        elif _unknown_word_before(toks, first[3], consumed):
            amount, unsure = None, True
    return {"amount": amount, "day": day, "amount_unsure": unsure}


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


def spoken_inr(n: int) -> str:
    """For text-to-speech: '2,500 rupees' (we do not know how every TTS voice reads the ₹ sign)."""
    return inr(n)[1:] + " rupees"


def assess(amount, day, today: dt.date, day_unsure: bool = False, amount_unsure: bool = False):
    """Given what we know so far, say what to ask or read back next."""
    when = resolve(day, today)
    low = day_unsure and day is None
    if amount is None and amount_unsure:
        ask = "I am not sure I heard the full amount. How much exactly? For example, three thousand rupees."
    elif amount is None and (day is None or low):
        ask = "I did not catch the amount or the day. Could you say both again?"
    elif amount is None:
        ask = "How much will you pay?"
    elif day is None or low:
        ask = f"I heard {spoken_inr(amount)}. On which day will you pay?"
    elif when is None:
        ask = f"I heard {spoken_inr(amount)} next week. Which day next week?"
    else:
        ask = f"I heard {spoken_inr(amount)} on {when.strftime('%A, %d %B')}. Is that right?"
    needs = amount is None or day is None or low or when is None
    summary = f"{spoken_inr(amount)} on {when.strftime('%A, %d %B %Y')}" if not needs else None
    return {"amount": amount, "day": day, "date": when, "confirm_prompt": ask,
            "needs_clarification": needs, "summary": summary}


def extract(text: str, today: dt.date):
    """One utterance, nothing known before."""
    return turn(text, today)


def turn(text: str, today: dt.date, amount=None, day=None):
    """One caller utterance merged with what we already know. New information replaces old;
    a doubtful day (low confidence) is never stored, the agent asks instead."""
    p = parse(text)
    new_day = p["day"] if p["day"] and p["day"]["conf"] == "high" else None
    unsure = bool(p["day"] and p["day"]["conf"] == "low")
    if p["amount_unsure"]:
        amount = None
    return assess(p["amount"] if p["amount"] is not None else amount, new_day or day, today,
                  day_unsure=unsure, amount_unsure=p["amount_unsure"])


# ---------------------------------------------------------------- yes / no after the read-back
_YES_RAW = ("ஆம", "சரி", "யெஸ்", "எஸ்", "கரெக்ட்", "கரக்ட்", "ரைட்", "ஓகே", "ஒகே")
_YES_EN = ("yes", "yeah", "yep", "correct", "right", "ok", "okay", "sure")
_NO_RAW = ("இல்ல", "நோ", "ராங்", "ரோங்", "தப்", "வேண்டா")
_NO_EN = ("no", "nope", "wrong", "incorrect")


def confirm_intent(text: str):
    """What the caller said after the read-back: yes, no (maybe with a correction), or unclear.
    Both a yes-word and a no-word in one reply is 'unclear' on purpose: for a payment, ask again."""
    toks = tokens(text)
    yes = any(t.startswith(_YES_RAW) or t in _YES_EN for t in toks)
    no = any(t.startswith(_NO_RAW) or t in _NO_EN for t in toks)
    if yes and not no:
        return {"intent": "yes", "amount": None, "day": None}
    if no and not yes:
        p = parse(text)                       # "இல்லை, த்ரீ தௌசண்ட்" = no, and the amount is 3000
        return {"intent": "no", "amount": p["amount"], "day": p["day"]}
    return {"intent": "unclear", "amount": None, "day": None}
