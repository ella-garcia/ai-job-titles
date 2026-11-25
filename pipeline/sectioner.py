"""Split posting body text into about / responsibilities / qualifications / benefits sections."""
from __future__ import annotations

import re
from html import unescape

# Heading → section key. First matching pattern wins for a heading line.
_HEADING_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("benefits", re.compile(
        r"^(benefits|perks|what we offer|compensation|pay & benefits|our benefits)\b", re.I)),
    ("qual", re.compile(
        r"^(qualifications|requirements|what you(?:'|’)ll? need|what we(?:'|’)re looking for|"
        r"you have|you bring|minimum qualifications|preferred qualifications|basic qualifications|"
        r"must[- ]have|nice[- ]to[- ]have|skills|experience required)\b", re.I)),
    ("resp", re.compile(
        r"^(responsibilities|what you(?:'|’)ll? do|what you will do|about the (?:role|job|position)|"
        r"the role|your role|day[- ]to[- ]day|in this role|you will|you(?:'|’)ll)\b", re.I)),
    ("about", re.compile(
        r"^(about (?:us|the company|anthropic|openai|the team)|who we are|our mission|"
        r"company overview|the company)\b", re.I)),
]

_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.I | re.S)
_HEADING_LINE = re.compile(
    r"(?m)^(?:\s*(?:[*\-•·]|\d+[.)])\s*)?"
    r"([A-Za-z][A-Za-z0-9 /&'’-]{2,60})"
    r"\s*:?\s*$"
)
_SPACE = re.compile(r"\s+")


def html_to_text(html: str | None) -> str:
    if not isinstance(html, str) or not html.strip():
        return ""
    text = unescape(unescape(html))
    # Turn block tags into newlines so headings stay on their own line.
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|br|tr)>", "\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = _TAG.sub(" ", text)
    text = text.replace("\xa0", " ")
    lines = [_SPACE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _section_for_heading(heading: str) -> str | None:
    h = heading.strip().strip(":").strip()
    for name, pattern in _HEADING_RULES:
        if pattern.search(h):
            return name
    return None


def section_text(text: str | None) -> dict[str, str]:
    """Return text_about / text_resp / text_qual / text_benefits.

    If no recognised headings are found, the full text goes into text_resp (analyses prefer that field).
    """
    raw = html_to_text(text) if text and "<" in text else (text or "")
    raw = raw.strip()
    buckets = {"about": [], "resp": [], "qual": [], "benefits": []}
    if not raw:
        return {f"text_{k}": "" for k in buckets}

    current = "resp"
    saw_heading = False
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        heading = None
        m = _HEADING_LINE.match(line)
        if m and len(line) <= 80:
            heading = _section_for_heading(m.group(1))
        if heading is None and len(line) <= 80:
            heading = _section_for_heading(line)
        if heading is not None:
            current = heading
            saw_heading = True
            continue
        buckets[current].append(line)

    if not saw_heading:
        buckets = {"about": [], "resp": [raw], "qual": [], "benefits": []}

    return {
        "text_about": "\n".join(buckets["about"]).strip(),
        "text_resp": "\n".join(buckets["resp"]).strip(),
        "text_qual": "\n".join(buckets["qual"]).strip(),
        "text_benefits": "\n".join(buckets["benefits"]).strip(),
    }
