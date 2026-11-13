"""Kaggle LinkedIn job-posting sets: download, keep the columns we use, save as Parquet.

Needs KAGGLE_USERNAME and KAGGLE_KEY. The unzipped CSVs stay in a temp folder and are deleted.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from .config import CFG, TODAY, data_dir, secret
from .manifest import log_download

KEEP = re.compile(r"title|company|description|summary|skill|listed|posted|date|location|level|url|link|id$", re.I)


def fetch_kaggle(date: str = TODAY) -> None:
    user, key = secret("KAGGLE_USERNAME"), secret("KAGGLE_KEY")
    if not (user and key):
        print("No KAGGLE_USERNAME / KAGGLE_KEY: skipping Kaggle.")
        return
    env = {**os.environ, "KAGGLE_USERNAME": user, "KAGGLE_KEY": key}
    for name, slug in CFG["kaggle"].items():
        dest = data_dir() / "raw" / name / date
        if dest.exists() and any(dest.glob("*.parquet")):
            print(f"already have {name}")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["kaggle", "datasets", "download", "-d", slug, "-p", tmp, "--unzip", "-q"],
                           check=True, env=env)
            for csv in sorted(Path(tmp).rglob("*.csv")):
                cols = [c for c in pd.read_csv(csv, nrows=0).columns if KEEP.search(c)]
                df = pd.read_csv(csv, usecols=cols, low_memory=False)
                parquet = dest / (csv.stem + ".parquet")
                df.to_parquet(parquet)
                log_download(name, f"kaggle://{slug}/{csv.name}", parquet, rows=len(df),
                             licence="scraped: aggregates only")
                print(f"{name}/{csv.name}: {len(df):,} rows, kept {cols}")
