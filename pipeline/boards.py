"""Full job boards on Greenhouse, Lever and Ashby: every open role, saved once per day.

Output: raw/boards/<date>/<system>_<company>.json.gz (the API response as-is, gzipped).
Older uncompressed .json snapshots are still read.
"""
import gzip
import json
from pathlib import Path

import pandas as pd

from .config import CFG, TODAY, data_dir
from .families import company_group, family
from .http import polite
from .manifest import log_download

BOARD_URL = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
}


def jobs_in(system: str, payload) -> list[dict]:
    return payload if system == "lever" else payload.get("jobs", [])


def job_title(job: dict) -> str:
    return job.get("text") or job.get("title") or ""


def read_snapshot(path: Path):
    """Parsed JSON of a board snapshot, gzipped or not."""
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def snapshot_files(folder: Path) -> list[Path]:
    """Snapshots in a date folder; if both forms exist for a board, the gzipped one wins."""
    files = {}
    for path in sorted(folder.glob("*.json")) + sorted(folder.glob("*.json.gz")):
        files[path.name.split(".")[0]] = path
    return [files[k] for k in sorted(files)]


def fetch_boards(date: str = TODAY) -> pd.DataFrame:
    """Download every configured board not yet saved for `date`. Returns one row per board."""
    out = data_dir() / "raw" / "boards" / date
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for system, names in CFG["boards"].items():
        for name in names:
            path = out / f"{system}_{name}.json.gz"
            legacy = out / f"{system}_{name}.json"
            if legacy.exists() and not path.exists():
                path = legacy
            if not path.exists():
                url = BOARD_URL[system].format(name)
                try:
                    response = polite("GET", url, timeout=180)
                except Exception as exc:
                    print(f"FAILED {system}/{name}: {exc}")
                    continue
                with gzip.open(path, "wt", encoding="utf-8") as fh:
                    fh.write(response.text)
                log_download(f"board_{system}", url, path, rows=len(jobs_in(system, response.json())),
                             licence="scraped: aggregates only")
            n_jobs = len(jobs_in(system, read_snapshot(path)))
            rows.append(dict(system=system, company=name, jobs=n_jobs, kb=path.stat().st_size // 1024))
            print(f"{system:10} {name:14} {n_jobs:5} jobs")
    return pd.DataFrame(rows)


def board_titles(date: str = TODAY) -> pd.DataFrame:
    """One row per open role on the saved boards: group, company, title, family."""
    rows = []
    for path in snapshot_files(data_dir() / "raw" / "boards" / date):
        system, company = path.name.split(".")[0].split("_", 1)
        for job in jobs_in(system, read_snapshot(path)):
            title = job_title(job)
            rows.append(dict(source="board", group=company_group(company), company=company,
                             title=title, family=family(title), spain=False))
    return pd.DataFrame(rows, columns=["source", "group", "company", "title", "family", "spain"])
