"""Preliminary Q1 rebrand test on one week of current postings (P2 only).

Can a TF-IDF + logistic-regression classifier tell FDE postings from Solutions Architect / Customer
Engineer postings, when it never sees the job title or the company it is tested on?

Read the FDE-vs-SA accuracy against two anchors run the same way:
  near-synonyms  "solutions architect" vs "solutions/customer engineer" titles  (expected: hard to separate)
  distinct roles  SA vs product manager                                          (expected: easy)

Not yet in place (steps 1 and 8 of the plan): sectioning, boilerplate removal, the golden set, and
earlier periods. Treat the numbers as a first look, not a finding.

Run: uv run python -m q1_rebrand.preview
"""
import json
import re
from html import unescape

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

from pipeline.boards import job_title, jobs_in, read_snapshot, snapshot_files
from pipeline.config import CFG, SEED, TODAY, data_dir, run_dir
from pipeline.employers import load_employers
from pipeline.families import company_group, family

PER_COMPANY_CAP = 40      # postings per company per class, so Amazon or Databricks can't dominate
MIN_PER_CLASS = 8         # a company must post at least this many of each class for the within-company test
N_PERMUTATIONS = 20       # label shuffles for the chance baseline

# --- Text ---------------------------------------------------------------------------------------

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
    {"aws", "amazon web services", "google", "scale ai", "glean", "t-mobile", "at&t", "telefónica",
     "claude", "chatgpt", "gpt", "foundry", "aip", "agentforce", "azure"}, key=len, reverse=True)
COMPANY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in COMPANY_WORDS) + r")\b", re.I)


def mask(text: str) -> str:
    return COMPANY_RE.sub(" ", TITLE_WORDS.sub(" ", text))


# --- Data ---------------------------------------------------------------------------------------

def load_postings(date: str = TODAY) -> pd.DataFrame:
    rows = []
    for path in snapshot_files(data_dir() / "raw" / "boards" / date):
        system, company = path.name.split(".")[0].split("_", 1)
        for job in jobs_in(system, read_snapshot(path)):
            title = job_title(job)
            rows.append({"company": company, "group": company_group(company), "title": title,
                         "family": family(title), "text": board_text(system, job)})
    emp = load_employers(date)
    for rec in emp.to_dict("records") if len(emp) else []:
        rows.append({"company": rec["employer"], "group": rec["group"], "title": rec["title"],
                     "family": family(rec["title"]), "text": html_to_text(rec.get("text"))})
    df = pd.DataFrame(rows)
    df = df[df.text.str.len() > 500]
    df = df[df.text.map(is_english)]
    df["masked"] = df.text.map(mask)
    # Location copies of one posting (common on Workday) count once
    df = df.drop_duplicates(subset=["company", "masked"])
    return df.reset_index(drop=True)


def subfamily(title: str) -> str:
    t = title.lower()
    if re.search(r"solutions? architect", t):
        return "architect"
    if re.search(r"solutions? engineer|customer engineer", t):
        return "engineer"
    return "other"


# --- Test ---------------------------------------------------------------------------------------

def balanced(df: pd.DataFrame, label: str, within_company: bool, rng: np.random.Generator) -> pd.DataFrame:
    """Cap each company per class; for the within-company test, keep companies that post both classes
    and take equal numbers of each from every company."""
    classes = sorted(df[label].unique())
    parts = []
    for _company, g in df.groupby("company"):
        counts = g[label].value_counts()
        if within_company:
            if any(counts.get(c, 0) < MIN_PER_CLASS for c in classes):
                continue
            n = min(PER_COMPANY_CAP, *(counts[c] for c in classes))
            caps = dict.fromkeys(classes, n)
        else:
            caps = {c: min(PER_COMPANY_CAP, counts.get(c, 0)) for c in classes}
        for c in classes:
            sub = g[g[label] == c]
            if caps[c]:
                parts.append(sub.sample(caps[c], random_state=int(rng.integers(1 << 31))))
    out = pd.concat(parts) if parts else df.iloc[0:0]
    if not within_company and len(out):  # equalise classes overall
        n = out[label].value_counts().min()
        out = out.groupby(label, group_keys=False).sample(n, random_state=SEED)
    return out.reset_index(drop=True)


def cross_validate(df: pd.DataFrame, label: str, positive: str) -> dict:
    y = (df[label] == positive).astype(int).to_numpy()
    groups = df.company.to_numpy()
    n_splits = min(5, df.company.nunique())
    if n_splits < 2:
        return {"error": "fewer than 2 companies"}
    folds = list(GroupKFold(n_splits=n_splits).split(df.masked, y, groups))

    def run(labels):
        pred = np.zeros_like(labels)
        for train, test in folds:
            vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, stop_words="english")
            x_train = vec.fit_transform(df.masked.iloc[train])
            model = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            model.fit(x_train, labels[train])
            pred[test] = model.predict(vec.transform(df.masked.iloc[test]))
        return pred

    pred = run(y)
    rng = np.random.default_rng(SEED)
    chance = [accuracy_score(p, run(p)) for p in (rng.permutation(y) for _ in range(N_PERMUTATIONS))]
    return {"n": int(len(df)), "n_positive": int(y.sum()), "companies": int(df.company.nunique()),
            "accuracy": round(accuracy_score(y, pred), 3), "macro_f1": round(f1_score(y, pred, average="macro"), 3),
            "chance_accuracy": round(float(np.mean(chance)), 3),
            "chance_95th": round(float(np.percentile(chance, 95)), 3)}


def top_terms(df: pd.DataFrame, label: str, positive: str, k: int = 25) -> pd.DataFrame:
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, stop_words="english")
    x = vec.fit_transform(df.masked)
    model = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced").fit(x, df[label] == positive)
    terms = np.array(vec.get_feature_names_out())
    order = np.argsort(model.coef_[0])
    return pd.DataFrame({f"more_{positive}": terms[order[::-1][:k]], "more_other": terms[order[:k]]})


def main() -> None:
    rng = np.random.default_rng(SEED)
    df = load_postings()
    out = run_dir()
    print(f"{len(df):,} English postings with text after de-duplication")

    fde_sa = df[df.family.isin(["fde", "sa_ce"])]
    sa = df[df.family == "sa_ce"].assign(sub=lambda d: d.title.map(subfamily))
    sa = sa[sa["sub"] != "other"]
    sa_pm = df[df.family.isin(["sa_ce", "pm"])]

    tests = {
        "FDE vs SA, all companies": (fde_sa, "family", "fde", False),
        "FDE vs SA, within companies posting both (headline)": (fde_sa, "family", "fde", True),
        "Anchor: architect vs engineer titles (near-synonyms)": (sa, "sub", "architect", True),
        "Anchor: SA vs PM (distinct roles)": (sa_pm, "family", "pm", True),
    }
    results = {}
    for name, (data, label, positive, within) in tests.items():
        sample = balanced(data, label, within, rng)
        results[name] = cross_validate(sample, label, positive) if len(sample) else {"error": "no data"}
        results[name]["companies_used"] = sorted(sample.company.unique().tolist())
        print(f"\n{name}\n  {results[name]}")

    headline = balanced(fde_sa, "family", True, np.random.default_rng(SEED))
    terms = top_terms(headline, "family", "fde")
    print("\nTerms that most separate FDE from SA postings (within companies):")
    print(terms.head(20).to_string(index=False))

    (out / "q1_preview.json").write_text(json.dumps(results, indent=2))
    terms.to_csv(out / "q1_preview_top_terms.csv", index=False)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
