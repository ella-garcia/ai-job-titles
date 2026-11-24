"""Stratified golden-set sample (family × period). Writes IDs and titles under AJT_DATA — not git."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from pipeline.boards import job_title, jobs_in, read_snapshot, snapshot_files
from pipeline.config import CFG, SEED, data_dir
from pipeline.employers import load_employers
from pipeline.families import company_group, family
from pipeline.titles import title_norm
from pipeline.wayback import period_of
from pipeline.wayback_postings import load_wayback
from q1_rebrand.data import board_text, html_to_text, snapshot_dates


def _posting_id(source: str, company: str, title: str, observed: str) -> str:
    raw = f"{source}|{company}|{title}|{observed}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _corpus() -> pd.DataFrame:
    rows: list[dict] = []
    for date in snapshot_dates():
        for path in snapshot_files(Path(data_dir() / "raw" / "boards" / date)):
            system, company = path.name.split(".")[0].split("_", 1)
            for job in jobs_in(system, read_snapshot(path)):
                title = job_title(job)
                text = board_text(system, job)
                rows.append({
                    "source": "board",
                    "company": company,
                    "group": company_group(company),
                    "title": title,
                    "title_norm": title_norm(title),
                    "family_auto": family(title),
                    "observed": date,
                    "period": period_of(date.replace("-", "")),
                    "has_text": bool(text and len(text) > 80),
                })
        emp = load_employers(date)
        if len(emp):
            for rec in emp.to_dict("records"):
                title = rec.get("title") or ""
                text = html_to_text(rec.get("text"))
                company = rec.get("employer") or ""
                rows.append({
                    "source": "search",
                    "company": company,
                    "group": company_group(company),
                    "title": title,
                    "title_norm": title_norm(title),
                    "family_auto": family(title),
                    "observed": date,
                    "period": period_of(date.replace("-", "")),
                    "has_text": bool(text and len(text) > 80),
                })
    wb = load_wayback()
    if not wb.empty:
        for rec in wb.to_dict("records"):
            title = rec.get("title") or ""
            company = rec.get("company") or ""
            ts = str(rec.get("ts") or "")
            observed = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ""
            rows.append({
                "source": "wayback",
                "company": company,
                "group": company_group(company),
                "title": title,
                "title_norm": title_norm(title),
                "family_auto": family(title),
                "observed": observed,
                "period": rec.get("period") or period_of(ts[:8]),
                "has_text": bool(rec.get("text")),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["posting_id"] = [
        _posting_id(s, c, t, o)
        for s, c, t, o in zip(df.source, df.company, df.title, df.observed, strict=True)
    ]
    # One row per posting_id (earliest observation).
    return df.sort_values("observed").drop_duplicates("posting_id", keep="first").reset_index(drop=True)


def sample(n: int | None = None, seed: int = SEED) -> pd.DataFrame:
    """Stratified sample by family_auto × period; falls back to family-only if a cell is empty."""
    target = n if n is not None else int(CFG.get("golden_set", {}).get("n", 150))
    df = _corpus()
    if df.empty:
        return df

    # Prefer cells that have body text (needed for ai_bullet).
    pool = df[df.has_text].copy() if df.has_text.any() else df.copy()
    pool = pool.assign(_r=pool.posting_id.map(lambda x: hashlib.sha1(f"{seed}|{x}".encode()).hexdigest()))
    pool = pool.sort_values("_r")

    cells = list(pool.groupby(["family_auto", "period"], dropna=False).groups.keys())
    if not cells:
        return pool.head(0)

    per_cell = max(1, target // len(cells))
    parts = []
    for _, g in pool.groupby(["family_auto", "period"], dropna=False):
        parts.append(g.head(per_cell))
    out = pd.concat(parts, ignore_index=True)

    # Top up to target from remaining rows if stratification undershoots.
    if len(out) < target:
        rest = pool[~pool.posting_id.isin(out.posting_id)].head(target - len(out))
        out = pd.concat([out, rest], ignore_index=True)
    elif len(out) > target:
        out = out.head(target)

    out = out.drop(columns=["_r"], errors="ignore")
    out["family_human"] = ""
    out["ai_bullet"] = ""
    out["section"] = ""
    out["notes"] = ""
    return out


def write_sample(n: int | None = None) -> Path:
    out_dir = data_dir() / "processed" / "golden"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = sample(n=n)
    # Do not write body text. Titles are needed for family labelling.
    cols = [
        "posting_id", "source", "company", "group", "title", "title_norm",
        "family_auto", "period", "observed", "has_text",
        "family_human", "ai_bullet", "section", "notes",
    ]
    path = out_dir / "sample.csv"
    if df.empty:
        pd.DataFrame(columns=cols).to_csv(path, index=False)
    else:
        df[cols].to_csv(path, index=False)
    meta = {
        "n": int(len(df)),
        "seed": SEED,
        "path": str(path),
        "guide": "validation/labelling_guide.md",
    }
    (out_dir / "sample_meta.json").write_text(json.dumps(meta, indent=2))
    # Empty templates for each author (local only).
    for who in ("a", "b"):
        tmpl = out_dir / f"labels_{who}.csv"
        if not tmpl.exists() and not df.empty:
            df[cols].to_csv(tmpl, index=False)
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m validation.sample_golden")
    parser.add_argument("-n", type=int, default=None, help="sample size (default config golden_set.n)")
    args = parser.parse_args(argv)
    path = write_sample(n=args.n)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
