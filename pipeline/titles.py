"""Title normalisation and seniority extraction (unified schema: title_raw / title_norm / seniority)."""
from __future__ import annotations

import re

# Ordered from more specific / higher rank so the first match is the reported seniority.
_SENIORITY_LEVELS: list[tuple[str, re.Pattern[str]]] = [
    ("intern", re.compile(r"\b(interns?|internship)\b", re.I)),
    ("junior", re.compile(r"\bjunior\b|\bjr\.?(?!\w)", re.I)),
    ("senior", re.compile(r"\bsenior\b|\bsr\.?(?!\w)", re.I)),
    ("staff", re.compile(r"\bstaff\b", re.I)),
    ("principal", re.compile(r"\bprincipal\b", re.I)),
    ("lead", re.compile(r"\blead\b", re.I)),
    ("director", re.compile(r"\bdirector\b", re.I)),
    ("vp", re.compile(r"\b(vp|vice[- ]president)\b", re.I)),
    ("head", re.compile(r"\bhead of\b", re.I)),
    ("chief", re.compile(r"\bchief\b", re.I)),
]

# Strip these from the normalised title (seniority words, location markers, req IDs).
# sr./jr. cannot use a trailing \b after the optional period ('.' and ' ' are both non-word).
_STRIP_SENIORITY = re.compile(
    r"\b(interns?|internship|junior|mid[- ]level|entry[- ]level|senior|staff|principal|"
    r"lead|head of|director|vp|vice[- ]president|chief)\b|\b(jr|sr)\.?(?!\w)",
    re.I,
)
_STRIP_LOCATION_PAREN = re.compile(
    r"\([^)]*\b(remote|hybrid|on[- ]?site|wfh|"
    r"san francisco|seattle|new york|london|madrid|barcelona|berlin|paris|austin|chicago|"
    r"toronto|sydney|singapore|dublin|amsterdam|zurich|tokyo|bengaluru|bangalore|"
    r"uk|usa|u\.s\.a\.|u\.s\.|emea|apac|na|latam|eu)\b[^)]*\)",
    re.I,
)
_STRIP_REQ = re.compile(r"\b(req(uisition)?|job|r)[-_# ]?\d{3,}\b", re.I)
_STRIP_REMOTE = re.compile(r"\b(remote|hybrid|on[- ]?site|wfh)\b", re.I)
_STRIP_PUNCT = re.compile(r"[,/|•·]+")
_STRIP_SPACE = re.compile(r"\s+")


def seniority(title: str | None) -> str | None:
    """Highest-priority seniority token in the title, or None if none match."""
    text = title or ""
    for name, pattern in _SENIORITY_LEVELS:
        if pattern.search(text):
            return name
    return None


def title_norm(title: str | None) -> str:
    """Lowercased title with seniority, location markers, team/req-IDs and extra punctuation stripped."""
    text = (title or "").lower()
    text = _STRIP_REQ.sub(" ", text)
    text = _STRIP_LOCATION_PAREN.sub(" ", text)
    text = _STRIP_SENIORITY.sub(" ", text)
    text = _STRIP_REMOTE.sub(" ", text)
    text = _STRIP_PUNCT.sub(" ", text)
    text = _STRIP_SPACE.sub(" ", text).strip(" -–—\t")
    return text
