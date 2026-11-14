"""Q1 corpus: postings with cleaned, masked text from every source and snapshot date.

Sources: full job boards and big-employer searches (one or more weekly snapshots) and archived
postings from the Wayback Machine. Every posting gets: source, company, title, family, sub (architect /
engineer for SA titles), observed date, period, cleaned text, masked text and a key (hash of company and
masked text) used to tell development and held-out postings apart.
"""
import hashlib
import re
from html import unescape
from pathlib import Path

import pandas as pd

from pipeline.boards import job_title, jobs_in, read_snapshot, snapshot_files
from pipeline.clean import remove_boilerplate
from pipeline.config import CFG, data_dir
from pipeline.employers import load_employers
from pipeline.families import company_group, family
from pipeline.wayback import period_of
from pipeline.wayback_postings import load_wayback

# --- Text helpers ---------------------------------------------------------------------------------

def html_to_text(html) -> str:
    if not isinstance(html, str):                  # None, or NaN from pandas
        return ""
    text = unescape(unescape(html))                # Greenhouse content is HTML-escaped twice
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def board_text(system: str, job: dict) -> str:
    if system == "greenhouse":
        return html_to_text(job.get("content"))
    if system == "lever":
        lists = " ".join(f"{x.get('text', '')} {html_to_text(x.get('content'))}" for x in job.get("lists") or [])
        return " ".join([job.get("descriptionPlain") or "", lists, job.get("additionalPlain") or ""])
    return job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml"))


EN = {"the", "and", "you", "with", "our", "to", "of", "will", "for", "your"}
ES = {"de", "la", "y", "el", "en", "con", "para", "los", "las", "del"}


def is_english(text: str) -> bool:
    words = re.findall(r"[a-záéíóúñ]+", text.lower())
    en, es = sum(w in EN for w in words), sum(w in ES for w in words)
    return en >= 20 and en > 2 * es


# Title words and company names are masked: the test is about the work described, not the label.
TITLE_WORDS = re.compile(
    r"forward[- ]deployed|deployment strateg\w*|solutions?[- ]architect\w*|customer engineer\w*|"
    r"solutions?[- ]engineer\w*|product manag\w*|\bfdes?\b|\bsas?\b|\bpms?\b|\bces?\b", re.I)
COMPANY_WORDS = sorted(
    {n for names in CFG["boards"].values() for n in names} | set(CFG["employers"]) |
    set(CFG["wayback"].get("collect", {})) |
    {"aws", "amazon web services", "google", "scale ai", "glean", "t-mobile", "at&t", "telefónica",
     "palantir technologies", "claude", "chatgpt", "gpt", "foundry", "gotham", "aip", "agentforce", "azure"},
    key=len, reverse=True)
COMPANY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in COMPANY_WORDS) + r")\b", re.I)


def mask(text: str) -> str:
    return re.sub(r"\s+", " ", COMPANY_RE.sub(" ", TITLE_WORDS.sub(" ", text))).strip()


def subfamily(title: str) -> str:
    t = (title or "").lower()
    if re.search(r"solutions? architect", t):
        return "architect"
    if re.search(r"solutions? engineer|customer engineer", t):
        return "engineer"
    return "other"


def posting_key(company: str, masked: str) -> str:
    return hashlib.sha1(f"{company}|{masked}".encode()).hexdigest()[:16]


# --- Loading --------------------------------------------------------------------------------------

def snapshot_dates() -> list[str]:
    dates = set()
    for kind in ("boards", "employers"):
        folder = data_dir() / "raw" / kind
        if folder.exists():
            dates |= {p.name for p in folder.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)}
    return sorted(dates)


def current_postings(dates: list[str]) -> pd.DataFrame:
    rows = []
    for date in dates:
        for path in snapshot_files(Path(data_dir() / "raw" / "boards" / date)):
            system, company = path.name.split(".")[0].split("_", 1)
            for job in jobs_in(system, read_snapshot(path)):
                rows.append({"source": "board", "company": company, "title": job_title(job),
                             "text": board_text(system, job), "observed": date})
        emp = load_employers(date)
        for rec in emp.to_dict("records") if len(emp) else []:
            rows.append({"source": "search", "company": rec["employer"], "title": rec["title"],
                         "text": html_to_text(rec.get("text")), "observed": date})
    df = pd.DataFrame(rows, columns=["source", "company", "title", "text", "observed"])
    df["period"] = df.observed.str.replace("-", "").map(period_of)
    return df


def archive_postings() -> pd.DataFrame:
    wb = load_wayback()
    if wb.empty:
        return pd.DataFrame(columns=["source", "company", "title", "text", "observed", "period"])
    wb["observed"] = wb.ts.str[:4] + "-" + wb.ts.str[4:6] + "-" + wb.ts.str[6:8]
    return wb[["source", "company", "title", "text", "observed", "period"]]


def prepare(df: pd.DataFrame, protocol: dict) -> pd.DataFrame:
    """Clean, filter, mask and de-duplicate. Keeps the earliest observation of each posting."""
    if df.empty:
        return df.assign(family=[], sub=[], group=[], masked=[], key=[])
    df = df.reset_index(drop=True).copy()
    df["family"] = df.title.map(family)
    df["sub"] = df.title.map(subfamily)
    df["group"] = df.company.map(company_group)
    bp = protocol["boilerplate"]
    df["clean"] = remove_boilerplate(df, "text", ("company", "source"), bp["share"], bp["min_docs"])
    df = df[df.clean.str.len() >= protocol["min_chars"]]
    if protocol.get("english_only", True):
        df = df[df.clean.map(is_english)]
    df = df.assign(masked=df.clean.map(mask))
    df["key"] = [posting_key(c, m) for c, m in zip(df.company, df.masked, strict=True)]
    df = df.sort_values("observed").drop_duplicates("key", keep="first")   # location copies and repeat weeks
    return df.reset_index(drop=True)
