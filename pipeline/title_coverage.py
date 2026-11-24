"""Inventory scraped titles: family vs other coverage by source and company (aggregates only)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from .boards import job_title, jobs_in, read_snapshot, snapshot_files
from .config import data_dir, run_dir
from .employers import load_employers
from .families import company_group, family
from .titles import seniority, title_norm
from .wayback_postings import load_wayback


def snapshot_dates() -> list[str]:
    dates: set[str] = set()
    for kind in ("boards", "employers"):
        folder = data_dir() / "raw" / kind
        if folder.exists():
            dates |= {p.name for p in folder.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)}
    return sorted(dates)


def load_titles(dates: list[str] | None = None) -> pd.DataFrame:
    """One row per title observation across board and employer snapshots (and Wayback if present)."""
    dates = dates or snapshot_dates()
    rows: list[dict] = []
    for date in dates:
        for path in snapshot_files(Path(data_dir() / "raw" / "boards" / date)):
            system, company = path.name.split(".")[0].split("_", 1)
            for job in jobs_in(system, read_snapshot(path)):
                title = job_title(job)
                rows.append({
                    "source": "board",
                    "system": system,
                    "company": company,
                    "group": company_group(company),
                    "title": title,
                    "title_norm": title_norm(title),
                    "seniority": seniority(title),
                    "family": family(title),
                    "observed": date,
                })
        emp = load_employers(date)
        if len(emp):
            for rec in emp.to_dict("records"):
                title = rec.get("title") or ""
                company = rec.get("employer") or ""
                rows.append({
                    "source": "search",
                    "system": rec.get("system") or "",
                    "company": company,
                    "group": company_group(company),
                    "title": title,
                    "title_norm": title_norm(title),
                    "seniority": seniority(title),
                    "family": family(title),
                    "observed": date,
                })
    wb = load_wayback()
    if not wb.empty:
        for rec in wb.to_dict("records"):
            title = rec.get("title") or ""
            company = rec.get("company") or ""
            rows.append({
                "source": "wayback",
                "system": "wayback",
                "company": company,
                "group": company_group(company),
                "title": title,
                "title_norm": title_norm(title),
                "seniority": seniority(title),
                "family": family(title),
                "observed": (rec.get("ts") or "")[:8],
            })
    cols = ["source", "system", "company", "group", "title", "title_norm", "seniority", "family", "observed"]
    return pd.DataFrame(rows, columns=cols)


def report(dates: list[str] | None = None) -> dict:
    """Write aggregate coverage tables to runs/<date>/ and return a small summary dict."""
    titles = load_titles(dates)
    out = run_dir()
    if titles.empty:
        summary = {"postings": 0, "distinct_title_norm": 0, "other_share": None, "dates": dates or []}
        (out / "title_coverage_summary.json").write_text(json.dumps(summary, indent=2))
        return summary

    # Deduplicate by source/company/title_norm for distinct-title views; keep raw counts too.
    distinct = titles.drop_duplicates(["source", "company", "title_norm"])

    by_family = titles.family.value_counts(dropna=False).rename("postings").to_frame()
    by_family["distinct_titles"] = distinct.family.value_counts()
    by_family.to_csv(out / "title_coverage_by_family.csv")

    by_source = pd.crosstab(titles.source, titles.family, margins=True)
    by_source.to_csv(out / "title_coverage_by_source_family.csv")

    by_group = pd.crosstab(titles.group, titles.family, margins=True)
    by_group.to_csv(out / "title_coverage_by_group_family.csv")

    by_company = (
        titles.groupby(["company", "family"], dropna=False)
        .size()
        .rename("postings")
        .reset_index()
        .sort_values(["company", "postings"], ascending=[True, False])
    )
    by_company.to_csv(out / "title_coverage_by_company_family.csv", index=False)

    other = titles[titles.family == "other"]
    other_top = (
        other.title_norm.value_counts()
        .head(100)
        .rename("postings")
        .rename_axis("title_norm")
        .reset_index()
    )
    other_top.to_csv(out / "title_coverage_other_top100.csv", index=False)

    n = len(titles)
    summary = {
        "dates": dates or snapshot_dates(),
        "postings": int(n),
        "distinct_title_norm": int(titles.title_norm.nunique()),
        "companies": int(titles.company.nunique()),
        "other_postings": int((titles.family == "other").sum()),
        "other_share": round(float((titles.family == "other").mean()), 4) if n else None,
        "family_counts": {k: int(v) for k, v in titles.family.value_counts().items()},
        "ai_eng": int((titles.family == "ai_eng").sum()),
        "ai_consultant": int((titles.family == "ai_consultant").sum()),
    }
    (out / "title_coverage_summary.json").write_text(json.dumps(summary, indent=2))
    return summary
