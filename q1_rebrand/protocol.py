"""Load the Q1 protocol and the frozen configuration.

Freezing records the protocol's hash, the git commit, the freeze date and the keys of every
development posting. The final held-out run refuses to start if any of that no longer holds.
"""
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from pipeline.config import ROOT, data_dir

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.yaml"
FROZEN_DIR = HERE / "frozen"            # committed: hashes and dates only, no posting text
FROZEN = FROZEN_DIR / "frozen_config.json"
DEV_KEYS = FROZEN_DIR / "dev_keys.txt"


def load() -> dict:
    return yaml.safe_load(PROTOCOL.read_text())


def labelling() -> dict:
    """The parts of config.yaml and data.py that decide labels and masking: frozen with the protocol."""
    from pipeline.config import CFG

    from .data import COMPANY_WORDS, TITLE_WORDS
    return {"families": CFG["families"], "exclude_titles": CFG.get("exclude_titles"),
            "title_words": TITLE_WORDS.pattern, "company_words": COMPANY_WORDS}


def protocol_hash() -> str:
    """Hash of protocol.yaml plus the labelling rules (v2: a label change also invalidates the freeze)."""
    extra = json.dumps(labelling(), sort_keys=True).encode()
    return hashlib.sha256(PROTOCOL.read_bytes() + b"\n" + extra).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def results_dir() -> Path:
    path = data_dir() / "runs" / "q1"
    path.mkdir(parents=True, exist_ok=True)
    return path


def frozen() -> dict | None:
    return json.loads(FROZEN.read_text()) if FROZEN.exists() else None


def dev_keys() -> set[str]:
    return set(DEV_KEYS.read_text().split()) if DEV_KEYS.exists() else set()
