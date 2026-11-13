"""Wayback Machine coverage test: the week-1 go/no-go gate for same-company comparisons (Q1, Q8).

1. Count: archived posting URLs per prefix and period, from the CDX index.
2. Usability: fetch a sample of snapshots per period and check each has a title and a
   responsibilities-type section.

Responses are cached per prefix (one gzipped JSONL file), so an interrupted run resumes.
"""
import gzip
import json
import random
import re
from html import unescape

import pandas as pd

from .config import CFG, SEED, data_dir, run_dir
from .http import polite

CDX = "https://web.archive.org/cdx/search/cdx"
RESPONSIBILITIES = re.compile(r"responsibilit|what you.ll do|what you will do|the role|you will|your impact|"
                              r"about the role|day to day|in this role", re.I)


def _cache_dir():
    path = data_dir() / "cache" / "wayback"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(prefix: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", prefix.lower())


def period_of(timestamp: str) -> str | None:
    day = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    for name, (start, end) in CFG["periods"].items():
        if start <= day <= end:
            return name
    return None


def looks_like_posting(url: str) -> bool:
    """Posting pages carry a job ID: in the path (Lever UUID, Greenhouse number) or the query
    (old palantir.com/careers/OpenPosDetail?id=...). Apply forms and landing pages are skipped."""
    u = url.lower()
    if re.search(r"apply|landing|scholarship", u):
        return False
    if re.search(r"[?&](id|gh_jid|jid|jobid)=", u):
        return True
    last = u.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    return bool(re.search(r"[0-9a-f]{8}-|\d{5,}", last))


def cdx_rows(prefix: str) -> list[list[str]]:
    """[timestamp, original, mimetype] for each unique HTML URL under the prefix (cached)."""
    path = _cache_dir() / f"{_slug(prefix)}.cdx.json"
    if path.exists():
        return json.loads(path.read_text())
    r = polite("GET", CDX, timeout=300, params={
        "url": prefix, "matchType": "prefix", "output": "json", "fl": "timestamp,original,mimetype",
        "filter": "statuscode:200", "collapse": "urlkey"})
    rows = r.json()[1:] if r.text.strip() else []
    rows = [x for x in rows if "html" in x[2]]
    path.write_text(json.dumps(rows))
    return rows


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", html))).strip()


def page_title(html: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return unescape(m.group(1)).strip() if m else ""


def is_usable(rec: dict) -> bool:
    return rec["status"] == 200 and len(rec["title"]) > 3 and rec["chars"] > 800 and rec["has_resp"]


def _load_pages(prefix: str) -> dict:
    path, seen = _cache_dir() / f"{_slug(prefix)}.pages.jsonl.gz", {}
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                seen[rec["key"]] = rec
    return seen


def coverage() -> dict[str, pd.DataFrame]:
    cfg = CFG["wayback"]
    rng = random.Random(SEED)
    count_rows, usable_rows = [], []
    for company, prefixes in cfg["prefixes"].items():
        for prefix in prefixes:
            rows = cdx_rows(prefix)
            print(f"{prefix}: {len(rows)} unique URLs")
            for ts, url, _ in rows:
                count_rows.append(dict(company=company, prefix=prefix, period=period_of(ts), year=ts[:4],
                                       posting_like=looks_like_posting(url)))
            postings = [x for x in rows if looks_like_posting(x[1])]
            seen = _load_pages(prefix)
            with gzip.open(_cache_dir() / f"{_slug(prefix)}.pages.jsonl.gz", "at", encoding="utf-8") as fh:
                for period in CFG["periods"]:
                    pool = [x for x in postings if period_of(x[0]) == period]
                    for ts, url, _ in rng.sample(pool, min(cfg["snapshots_per_cell"], len(pool))):
                        key = f"{ts}|{url}"
                        if key not in seen:
                            try:
                                r = polite("GET", f"https://web.archive.org/web/{ts}id_/{url}", timeout=60,
                                           gap=cfg["min_interval"], headers={"Accept": "text/html"}, max_tries=2)
                                status, html = r.status_code, r.text
                            except Exception:
                                status, html = 0, ""
                            text = strip_html(html)
                            seen[key] = dict(key=key, status=status, title=page_title(html), chars=len(text),
                                             has_resp=bool(RESPONSIBILITIES.search(text)))
                            fh.write(json.dumps(seen[key]) + "\n")
                        usable_rows.append(dict(company=company, prefix=prefix, period=period,
                                                usable=is_usable(seen[key])))

    counts = pd.DataFrame(count_rows, columns=["company", "prefix", "period", "year", "posting_like"])
    usable = pd.DataFrame(usable_rows, columns=["company", "prefix", "period", "usable"])
    by_year = counts[counts.posting_like].pivot_table(index="prefix", columns="year", aggfunc="size", fill_value=0)
    n_urls = counts[counts.posting_like].groupby(["company", "prefix", "period"]).size().rename("urls")
    share = usable.groupby(["company", "prefix", "period"]).usable.mean().rename("usable_share")
    estimate = pd.concat([n_urls, share], axis=1).fillna(0)
    estimate["est_usable"] = (estimate.urls * estimate.usable_share).round().astype(int)

    out = run_dir()
    by_year.to_csv(out / "wayback_urls_by_year.csv")
    usable.groupby(["company", "prefix", "period"]).usable.agg(["sum", "count"]).to_csv(out / "wayback_usability.csv")
    estimate.to_csv(out / "wayback_estimate.csv")
    return dict(by_year=by_year, estimate=estimate)
