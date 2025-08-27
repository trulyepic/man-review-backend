# app/moderation/profanity.py
from __future__ import annotations

import re

BAD_WORDS = {
    # keep lowercase; single tokens only here
    "ass",
    "fuck",
    "shit",
    "bitch",
    # add more…
}

# \b isn't perfect with all unicode; this adds basic unicode letter/digit boundary support
WORD = r"[^\W_]+"  # letters/digits (no underscore), unicode-aware with re.UNICODE
BOUND = r"(?<!\w)|\b"  # fall back to \b; engines vary. You can use (?:^|(?<=\W)) as well.

_patterns = [
    re.compile(rf"(?i)(?:^|(?<=\W))({re.escape(w)})(?=$|\W)", re.UNICODE)
    for w in BAD_WORDS
]

def contains_profanity(text: str) -> str | None:
    t = text or ""
    for pat in _patterns:
        m = pat.search(t)
        if m:
            return m.group(1)
    return None

def ensure_clean(text: str) -> None:
    hit = contains_profanity(text)
    if hit:
        # you can customize this message
        raise ValueError(f"Reply contains inappropriate language: “{hit}”.")
