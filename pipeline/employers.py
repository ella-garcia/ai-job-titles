"""Big employers (Magnificent 7, consulting, large tech, telcos) searched by role keyword.

Their careers sites have search APIs, not full boards, so we search every term in config.yaml and keep
the union. Full text is fetched only for titles in a target family; other titles are kept (title only)
for title-growth counts.

Output: raw/employers/<date>/<employer>.jsonl.gz, written when an employer finishes, so a re-run
skips employers already done that day.
"""
import gzip
import json
import re
import time
from html import unescape

import pandas as pd

from .config import CFG, TODAY, data_dir
from .families import family, is_spain
from .http import polite
from .manifest import log_download


def _cap(cfg: dict) -> int:
    return int(cfg.get("max_per_term", CFG["max_per_term"]))


# --- Search functions: yield dicts with id, title, location, posted, url (+ text if the list has it) ---

def _workday_base(cfg: dict) -> str:
    return f"https://{cfg['host']}.myworkdayjobs.com/wday/cxs/{cfg['tenant']}/{cfg['site']}"


def search_workday(cfg: dict, term: str):
    base, offset, total = _workday_base(cfg), 0, None
    while True:
        d = polite("POST", base + "/jobs",
                   json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term}).json()
        if total is None:
            total = d.get("total", 0)  # later pages report total = 0
        posts = d.get("jobPostings", [])
        for p in posts:
            yield dict(id=p["externalPath"], title=p.get("title", ""), location=p.get("locationsText"),
                       posted=p.get("postedOn"),
                       url=f"https://{cfg['host']}.myworkdayjobs.com/en-US/{cfg['site']}{p['externalPath']}")
        offset += len(posts)
        if not posts or offset >= min(total, _cap(cfg)):
            break


def search_amazon(cfg: dict, term: str):
    offset = 0
    while True:
        d = polite("GET", "https://www.amazon.jobs/en/search.json",
                   params={"base_query": term, "result_limit": 50, "offset": offset}).json()
        jobs = d.get("jobs", [])
        for j in jobs:
            parts = [j.get("description"),
                     j.get("basic_qualifications") and "Basic qualifications\n" + j["basic_qualifications"],
                     j.get("preferred_qualifications") and "Preferred qualifications\n" + j["preferred_qualifications"]]
            yield dict(id=j.get("id_icims") or j.get("id"), title=j.get("title", ""),
                       location=j.get("normalized_location") or j.get("location"), posted=j.get("posted_date"),
                       url="https://www.amazon.jobs" + (j.get("job_path") or ""),
                       text="\n\n".join(filter(None, parts)))
        offset += len(jobs)
        if not jobs or offset >= min(d.get("hits", 0), _cap(cfg)):
            break


MICROSOFT = "https://apply.careers.microsoft.com/api/pcsx"


def search_microsoft(cfg: dict, term: str):
    start = 0
    while True:
        d = polite("GET", MICROSOFT + "/search",
                   params={"domain": "microsoft.com", "query": term, "start": start}).json()["data"]
        positions = d.get("positions", [])
        for p in positions:
            yield dict(id=p["id"], title=p.get("name", ""), location="; ".join(p.get("locations") or []),
                       posted=p.get("postedTs"), url=p.get("positionUrl"))
        start += len(positions)
        if not positions or start >= min(d.get("count", 0), _cap(cfg)):
            break


def search_capgemini(cfg: dict, term: str):
    page, got = 1, 0
    while True:
        d = polite("GET", "https://cg-job-search-microservices.azurewebsites.net/api/job-search",
                   params={"page": page, "size": 50, "search": term}).json()
        jobs = d.get("data", [])
        for j in jobs:
            yield dict(id=j.get("id"), title=j.get("title", ""), location=j.get("location"),
                       posted=j.get("updated_at"), url=j.get("apply_job_url") or j.get("wp_url"),
                       text=j.get("description"))
        got += len(jobs)
        page += 1
        if not jobs or got >= min(d.get("count", 0), _cap(cfg)):
            break


def search_smartrecruiters(cfg: dict, term: str):
    offset, limit = 0, min(100, _cap(cfg))
    while True:
        d = polite("GET", f"https://api.smartrecruiters.com/v1/companies/{cfg['company']}/postings",
                   params={"q": term, "limit": limit, "offset": offset}).json()
        posts = d.get("content", [])
        for p in posts:
            loc = p.get("location") or {}
            yield dict(id=p["id"], title=p.get("name", ""), location=loc.get("fullLocation") or loc.get("city"),
                       posted=p.get("releasedDate"),
                       url=f"https://jobs.smartrecruiters.com/{cfg['company']}/{p['id']}")
        offset += len(posts)
        if not posts or offset >= min(d.get("totalFound", 0), _cap(cfg)):
            break


def _cdata(text: str) -> str:
    return unescape(re.sub(r"^<!\[CDATA\[|\]\]>$", "", text.strip()))


def parse_successfactors_rss(xml: str):
    """Items of a SuccessFactors job RSS feed. Titles look like 'Title (CITY, ES)'."""
    def tag(item: str, name: str) -> str:
        m = re.search(rf"(?s)<{name}>(.*?)</{name}>", item)
        return _cdata(m.group(1)) if m else ""

    for item in re.findall(r"(?s)<item>(.*?)</item>", xml):
        title = tag(item, "title")
        m = re.match(r"(.*)\(([^()]*)\)\s*$", title)
        yield dict(id=tag(item, "link"), title=(m.group(1) if m else title).strip(),
                   location=m.group(2) if m else None, posted=tag(item, "pubDate"), url=tag(item, "link"),
                   text=tag(item, "description"))


def search_successfactors(cfg: dict, term: str):
    # RSS feed per search: about 20 newest matches, no paging
    r = polite("GET", f"https://{cfg['host']}/services/rss/job/", params={"locale": "en_US", "keywords": term},
               headers={"Accept": "application/rss+xml, application/xml"})
    yield from parse_successfactors_rss(r.text)


# --- Detail functions: full text (and a better location) for one posting ---

def detail_workday(cfg: dict, rec: dict) -> dict:
    j = polite("GET", _workday_base(cfg) + rec["id"]).json().get("jobPostingInfo", {})
    locations = [j.get("location")] + [x.get("descriptor") for x in j.get("additionalLocations", [])
                                       if isinstance(x, dict)]
    return {"text": j.get("jobDescription", ""), "country": (j.get("country") or {}).get("descriptor"),
            "location": "; ".join(filter(None, locations)) or rec.get("location")}


def detail_microsoft(cfg: dict, rec: dict) -> dict:
    d = polite("GET", MICROSOFT + "/position_details",
               params={"position_id": rec["id"], "domain": "microsoft.com", "hl": "en"}).json()["data"]
    return {"text": d.get("jobDescription") or d.get("description") or json.dumps(d)}


def detail_smartrecruiters(cfg: dict, rec: dict) -> dict:
    d = polite("GET", f"https://api.smartrecruiters.com/v1/companies/{cfg['company']}/postings/{rec['id']}").json()
    sections = d.get("jobAd", {}).get("sections", {})
    text = "\n\n".join(f"{s.get('title', k)}\n{s.get('text', '')}" for k, s in sections.items() if s.get("text"))
    return {"text": text, "country": (d.get("location") or {}).get("country")}


SEARCH = {"workday": search_workday, "amazon": search_amazon, "microsoft": search_microsoft,
          "capgemini": search_capgemini, "smartrecruiters": search_smartrecruiters,
          "successfactors": search_successfactors}
DETAIL = {"workday": detail_workday, "microsoft": detail_microsoft, "smartrecruiters": detail_smartrecruiters}


def collect_employer(name: str, cfg: dict, terms: list[str]) -> list[dict]:
    seen: dict[str, dict] = {}
    for term in terms:
        for rec in SEARCH[cfg["system"]](cfg, term):
            key = str(rec["id"])
            if key in seen:
                seen[key]["terms"].append(term)
                continue
            rec.update(employer=name, group=cfg["group"], system=cfg["system"], terms=[term],
                       family=family(rec["title"]), observed=TODAY)
            seen[key] = rec
    if cfg["system"] in DETAIL:
        for rec in seen.values():
            if rec["family"] != "other" and not rec.get("text"):
                try:
                    rec.update(DETAIL[cfg["system"]](cfg, rec))
                except Exception as exc:
                    rec["text_error"] = str(exc)[:200]
    for rec in seen.values():
        rec["spain"] = is_spain(str(rec.get("location") or ""), str(rec.get("country") or ""))
    return list(seen.values())


def fetch_employers(only: list[str] | None = None, terms: list[str] | None = None, date: str = TODAY) -> None:
    out = data_dir() / "raw" / "employers" / date
    out.mkdir(parents=True, exist_ok=True)
    terms = terms or CFG["search_terms"]
    for name, cfg in CFG["employers"].items():
        if only and name not in only:
            continue
        path = out / f"{name}.jsonl.gz"
        if path.exists():
            print(f"already have {name}")
            continue
        t0 = time.time()
        try:
            records = collect_employer(name, cfg, terms)
        except Exception as exc:
            print(f"FAILED {name}: {exc}  (re-run to retry; finished employers are skipped)")
            continue
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, default=str) + "\n")
        tmp.rename(path)
        log_download(f"employer_{cfg['system']}", f"{cfg['system']}:{name}", path, rows=len(records),
                     licence="scraped: aggregates only")
        n_target = sum(r["family"] != "other" for r in records)
        print(f"{name:15} {len(records):5} listings, {n_target:4} in target families, {time.time() - t0:5.0f}s")


def load_employers(date: str = TODAY) -> pd.DataFrame:
    rows = []
    for path in sorted((data_dir() / "raw" / "employers" / date).glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            rows += [json.loads(line) for line in fh]
    return pd.DataFrame(rows)
