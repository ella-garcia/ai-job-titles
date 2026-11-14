"""Archived job postings from the Wayback Machine: title and text, for comparisons over time (Q1, Q8).

For each prefix in config `wayback.collect`:
1. List archived posting URLs from the CDX index (cached by `wayback.cdx_rows`).
2. Keep one snapshot per job (the earliest), so a job archived many times counts once; its period is
   the period of that first snapshot.
3. If the URL itself carries the title (e.g. databricks.com/company/careers/.../partner-solutions-architect-83478800),
   skip URLs whose title is not a target family without fetching them. Otherwise every URL must be fetched.
4. Fetch at most `max_per_cell` jobs per prefix and period, extract the title and text, label the family.

Output: raw/wayback/<prefix-slug>.jsonl, one record appended per page, so an interrupted run resumes
and loses at most the last line.
Stops politely after repeated connection failures (the Archive blocks clients after heavy use).
"""
import random
import re
from html import unescape

import pandas as pd
import requests

from .config import CFG, SEED, data_dir
from .families import family
from .http import polite
from .jsonl import append, read_lenient
from .wayback import _slug, cdx_rows, looks_like_posting, period_of, strip_html

TARGET = {"fde", "sa_ce", "pm", "ai_pm"}
GENERIC_HEADINGS = re.compile(
    r"^(open positions?|careers?|jobs?|job openings?|current openings|join us|apply( now)?)$", re.I)


def job_key(url: str) -> str:
    """One key per job: scheme, port, www and tracking parameters removed; an ?id= / gh_jid= kept."""
    u = re.sub(r"^https?://(www\.)?", "", url.lower())
    u = re.sub(r":80(?=/)", "", u)
    path, _, query = u.partition("?")
    job_id = re.search(r"(?:^|&)(id|gh_jid|jid|jobid)=([^&]+)", query)
    return path.rstrip("/") + (f"?{job_id.group(1)}={job_id.group(2)}" if job_id else "")


def title_from_url(url: str) -> str | None:
    """A readable title from the URL's last path segment, or None if it is only an ID."""
    last = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    last = re.sub(r"[-_]?\d{5,}$", "", last)                    # trailing numeric job ID
    words = [w for w in re.split(r"[-_+]+", last) if w]
    if len(words) < 2 or re.fullmatch(r"[0-9a-f-]{20,}", last):  # UUID or too short to be a title
        return None
    return " ".join(words)


def extract_title(html: str, company: str) -> str:
    """Job title from the page: og:title, then the first <h1>/<h2> that isn't the company or a generic
    heading, then <title> with the site name removed."""
    m = re.search(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
    candidates = [m.group(1)] if m else []
    for tag in ("h1", "h2"):
        candidates += re.findall(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", html)
    t = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if t:
        candidates.append(re.split(r"\s[|\-–—]\s", unescape(t.group(1)))[0])
    name = re.escape(company)
    for c in candidates:
        c = re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", c))).replace("\xa0", " ").strip()
        c = re.sub(rf"(?i)^{name}( technologies| inc\.?)?\s*[-–—|:]\s*", "", c)   # "Palantir Technologies - X"
        c = re.sub(rf"(?i)\s*[-–—|]\s*{name}\b.*$", "", c)                        # "X | Databricks"
        if len(c) > 3 and c.lower() != company.lower() and not GENERIC_HEADINGS.match(c):
            return c[:200]
    return ""


def candidates(company: str, prefix: str, max_per_cell: int, rng: random.Random,
               periods: list[str] | None = None, max_id_only: int | None = None) -> list[dict]:
    """Jobs to fetch for one prefix: earliest snapshot per job, URL-title filter, capped per period."""
    first: dict[str, tuple[str, str]] = {}
    for ts, url, _ in cdx_rows(prefix):
        if looks_like_posting(url):
            key = job_key(url)
            if key not in first or ts < first[key][0]:
                first[key] = (ts, url)
    by_period: dict[str, list[dict]] = {}
    for key, (ts, url) in first.items():
        period = period_of(ts)
        if not period or (periods and period not in periods):
            continue
        url_title = title_from_url(url)
        if url_title and family(url_title) not in TARGET:
            continue
        by_period.setdefault(period, []).append({"key": key, "ts": ts, "url": url, "url_title": url_title,
                                                 "company": company, "prefix": prefix, "period": period})
    chosen = []
    for period in sorted(by_period):
        pool = sorted(by_period[period], key=lambda c: c["key"])
        id_only = sum(c["url_title"] is None for c in pool) > len(pool) / 2
        cap = max_id_only if (id_only and max_id_only) else max_per_cell
        chosen += rng.sample(pool, min(cap, len(pool)))
    return chosen


def _out_path(prefix: str):
    folder = data_dir() / "raw" / "wayback"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{_slug(prefix)}.jsonl"
    legacy = folder / f"{_slug(prefix)}.jsonl.gz"       # earlier format: convert once
    if legacy.exists() and not path.exists():
        for rec in read_lenient(legacy):
            append(path, rec)
        legacy.unlink()
    return path


def _done(prefix: str) -> set[str]:
    path = _out_path(prefix)
    if not path.exists():
        return set()
    return {r["key"] for r in read_lenient(path) if r["status"] != 0}  # failed downloads are retried


def collect(max_per_cell: int | None = None, only: list[str] | None = None, max_failures: int = 10) -> None:
    cfg = CFG["wayback"]
    max_per_cell = max_per_cell or cfg["max_per_cell"]
    rng = random.Random(SEED)
    failures = 0
    for company, prefixes in cfg["collect"].items():
        if only and company not in only:
            continue
        for prefix in prefixes:
            try:
                todo = candidates(company, prefix, max_per_cell, rng, cfg.get("collect_periods"),
                                  cfg.get("max_per_cell_id_only"))
            except Exception as exc:
                print(f"SKIPPED {prefix}: {exc}")
                continue
            done = _done(prefix)
            todo = [c for c in todo if c["key"] not in done]
            print(f"{prefix}: {len(todo)} to fetch ({len(done)} already saved)")
            path = _out_path(prefix)
            for c in todo:
                try:
                    r = polite("GET", f"https://web.archive.org/web/{c['ts']}id_/{c['url']}", timeout=60,
                               gap=cfg["min_interval"], headers={"Accept": "text/html"}, max_tries=2)
                    status, html = r.status_code, r.text
                    failures = 0
                except requests.HTTPError as exc:
                    status, html = (exc.response.status_code if exc.response is not None else 0), ""
                except Exception:
                    status, html = 0, ""
                    failures += 1
                title = extract_title(html, company) or c["url_title"] or ""
                rec = {**c, "source": "wayback", "status": status, "title": title,
                       "family": family(title), "text": strip_html(html)}
                append(path, rec)
                if failures >= max_failures:
                    print(f"STOPPED: {failures} connection failures in a row; the Archive is probably "
                          "blocking us. Re-run later: saved postings are kept.")
                    return


def load_wayback() -> pd.DataFrame:
    """Every saved archived posting with a title and text (latest record per job)."""
    rows = {}
    folder = data_dir() / "raw" / "wayback"
    for path in sorted(folder.glob("*.jsonl")) + sorted(folder.glob("*.jsonl.gz")):
        for rec in read_lenient(path):
            if rec["status"] == 200 and rec["text"]:
                rec["family"] = family(rec["title"])  # relabel, so pattern fixes apply
                rows[(rec["prefix"], rec["key"])] = rec
    return pd.DataFrame(list(rows.values()))
