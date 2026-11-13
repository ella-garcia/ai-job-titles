"""manifest.csv in the data folder: one row per downloaded file (source, URL, date, sha256, rows, licence)."""
import hashlib
from pathlib import Path

import pandas as pd

from .config import TODAY, data_dir

COLUMNS = ["source", "url", "date", "file", "sha256", "rows", "licence"]


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def log_download(source: str, url: str, path: Path, rows: int | None = None, licence: str = "") -> None:
    root = data_dir()
    manifest = root / "manifest.csv"
    row = dict(source=source, url=url, date=TODAY, file=str(Path(path).resolve().relative_to(root)),
               sha256=sha256(path), rows=rows, licence=licence)
    df = pd.read_csv(manifest) if manifest.exists() else pd.DataFrame(columns=COLUMNS)
    df = df[df["file"] != row["file"]]  # a re-run replaces its own row
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(manifest, index=False)


def read_manifest() -> pd.DataFrame:
    manifest = data_dir() / "manifest.csv"
    return pd.read_csv(manifest) if manifest.exists() else pd.DataFrame(columns=COLUMNS)
