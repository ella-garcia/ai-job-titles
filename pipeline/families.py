"""Seed role-family labels from titles (regexes in config.yaml). Step 2 refines these with clustering."""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from .config import CFG, ROOT
from .titles import title_norm

FAMILY_PATTERNS = {name: re.compile(pattern, re.I) for name, pattern in CFG["families"].items()}
SPAIN = re.compile(CFG["spain_pattern"], re.I)
EXCLUDE = re.compile(CFG["exclude_titles"], re.I) if CFG.get("exclude_titles") else None
_overrides_cfg = CFG.get("family_overrides_path", "pipeline/family_overrides.csv")
OVERRIDES_PATH = Path(_overrides_cfg)
if not OVERRIDES_PATH.is_absolute():
    OVERRIDES_PATH = ROOT / OVERRIDES_PATH


@lru_cache(maxsize=1)
def _overrides() -> dict[str, str]:
    """title_norm → family from the hand-labelled overrides file (auditable clustering decisions)."""
    path = OVERRIDES_PATH
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row.get("title_norm") or "").strip()
            label = (row.get("family") or "").strip()
            if key and label:
                out[key] = label
    return out


def reload_overrides() -> None:
    """Clear the overrides cache (tests and after editing the CSV)."""
    _overrides.cache_clear()


def family(title: str | None) -> str:
    """First family whose pattern matches the normalised title, else an override, else 'other'.

    Excluded titles are always 'other'. Overrides apply only when no regex matched, so seed patterns
    stay the source of truth for Q1 families unless a leftover cluster is hand-labelled.
    """
    raw = title or ""
    text = title_norm(raw)
    # Exclusions still see the lowercased raw title so hardware/location words are not stripped away.
    if EXCLUDE and EXCLUDE.search(raw.lower()):
        return "other"
    for name, pattern in FAMILY_PATTERNS.items():
        if pattern.search(text) or pattern.search(raw.lower()):
            return name
    return _overrides().get(text, "other")


def is_spain(*location_parts: str | None) -> bool:
    return bool(SPAIN.search(" ".join(p for p in location_parts if p)))


def company_group(company: str) -> str:
    return CFG.get("company_group", {}).get(company, "other")
