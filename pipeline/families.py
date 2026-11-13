"""Seed role-family labels from titles (regexes in config.yaml). Step 2 refines these with clustering."""
import re

from .config import CFG

FAMILY_PATTERNS = {name: re.compile(pattern, re.I) for name, pattern in CFG["families"].items()}
SPAIN = re.compile(CFG["spain_pattern"], re.I)


def family(title: str | None) -> str:
    """First family whose pattern matches the title, else 'other'."""
    text = (title or "").lower()
    for name, pattern in FAMILY_PATTERNS.items():
        if pattern.search(text):
            return name
    return "other"


def is_spain(*location_parts: str | None) -> bool:
    return bool(SPAIN.search(" ".join(p for p in location_parts if p)))


def company_group(company: str) -> str:
    return CFG.get("company_group", {}).get(company, "other")
