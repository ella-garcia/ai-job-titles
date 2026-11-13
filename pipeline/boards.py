"""Full job boards on Greenhouse, Lever and Ashby: every open role, saved once per day.

Output: raw/boards/<date>/<system>_<company>.json (the API response as-is).
"""
import json

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


def fetch_boards(date: str = TODAY) -> pd.DataFrame:
    """Download every configured board not yet saved for `date`. Returns one row per board."""
    out = data_dir() / "raw" / "boards" / date
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for system, names in CFG["boards"].items():
        for name in names:
            path = out / f"{system}_{name}.json"
            if not path.exists():
                url = BOARD_URL[system].format(name)
                try:
                    response = polite("GET", url, timeout=180)
                except Exception as exc:
                    print(f"FAILED {system}/{name}: {exc}")
                    continue
                path.write_text(response.text, encoding="utf-8")
                log_download(f"board_{system}", url, path, rows=len(jobs_in(system, response.json())),
                             licence="scraped: aggregates only")
            n_jobs = len(jobs_in(system, json.loads(path.read_text(encoding="utf-8"))))
            rows.append(dict(system=system, company=name, jobs=n_jobs, kb=path.stat().st_size // 1024))
            print(f"{system:10} {name:14} {n_jobs:5} jobs")
    return pd.DataFrame(rows)


def board_titles(date: str = TODAY) -> pd.DataFrame:
    """One row per open role on the saved boards: group, company, title, family."""
    rows = []
    for path in sorted((data_dir() / "raw" / "boards" / date).glob("*.json")):
        system, company = path.stem.split("_", 1)
        for job in jobs_in(system, json.loads(path.read_text(encoding="utf-8"))):
            title = job_title(job)
            rows.append(dict(source="board", group=company_group(company), company=company,
                             title=title, family=family(title), spain=False))
    return pd.DataFrame(rows, columns=["source", "group", "company", "title", "family", "spain"])
