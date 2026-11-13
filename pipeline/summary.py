"""Week-1 summary: coverage by company group and family, plus the numbers for the go/no-go call."""
import json

import pandas as pd

from .boards import board_titles
from .config import TODAY, run_dir
from .employers import load_employers


def all_titles(date: str = TODAY) -> pd.DataFrame:
    boards = board_titles(date)
    emp = load_employers(date)
    if len(emp):
        emp = (emp.rename(columns={"employer": "company"})[["group", "company", "title", "family", "spain"]]
               .assign(source="search"))
    return pd.concat([boards, emp], ignore_index=True)


def coverage(date: str = TODAY) -> pd.DataFrame:
    titles = all_titles(date)
    table = pd.crosstab(titles.group, titles.family, margins=True)
    table.to_csv(run_dir() / "coverage_group_family.csv")
    return table


def week1_summary(date: str = TODAY) -> dict:
    titles = all_titles(date)
    out = run_dir()
    summary = {
        "date": date,
        "postings_total": int(len(titles)),
        "companies": int(titles.company.nunique()),
        "fde_postings": int((titles.family == "fde").sum()),
        "sa_ce_postings": int((titles.family == "sa_ce").sum()),
        "target_family_postings_in_spain": int(((titles.family != "other") & titles.spain).sum()),
    }
    estimate = out / "wayback_estimate.csv"
    if estimate.exists():
        est = pd.read_csv(estimate)
        summary["wayback_est_usable_by_period"] = est.groupby("period").est_usable.sum().astype(int).to_dict()
    (out / "week1_summary.json").write_text(json.dumps(summary, indent=2))
    return summary
