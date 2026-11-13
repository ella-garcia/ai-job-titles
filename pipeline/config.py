"""Project settings: config.yaml, the data folder, secrets and the run folder.

Works the same on a laptop and in Colab. Locally, settings come from `.env`; in Colab, from the
Colab secrets panel.
"""
import datetime
import os
import random
from pathlib import Path

import numpy as np
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
SEED = CFG["seed"]
TODAY = datetime.date.today().isoformat()
USER_AGENT = f"ai-job-titles-research (+https://github.com/{CFG['repo']})"


def secret(name: str) -> str | None:
    """Environment variable, or a Colab secret when running in Colab."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        from google.colab import userdata  # type: ignore

        return userdata.get(name)
    except Exception:
        return None


def data_dir() -> Path:
    """Root of the data folder (AJT_DATA, default ./data), with its standard subfolders."""
    root = Path(os.path.expanduser(secret("AJT_DATA") or str(ROOT / "data")))
    if not root.is_absolute():
        root = ROOT / root
    for sub in ("raw", "processed", "cache", "runs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root.resolve()


def run_dir() -> Path:
    """Folder for today's results: runs/<date>/."""
    path = data_dir() / "runs" / TODAY
    path.mkdir(parents=True, exist_ok=True)
    return path


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
