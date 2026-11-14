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


def protocol_hash() -> str:
    return hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()


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
