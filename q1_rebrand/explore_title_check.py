"""Exploratory title check: which companies' FDE postings read like SA postings?

Outside the frozen protocol. Every FDE and SA posting (development and held-out snapshots) is scored with
P(FDE) by a model that never trained on its company, and the share of a company's FDE postings scoring
below a cut-off is reported.

Two cleanings are compared, because company descriptions can make every posting from one employer look
alike:

  frozen       the protocol's cleaning (a sentence in over 30% of a company's postings is dropped)
  no_company   as frozen, plus company text removed: a sentence is dropped when it appears in 3 or more
               of the company's postings AND in at least one posting outside the FDE and SA families.
               A sentence that recruiters, PMs and engineers all share describes the employer, not the role.
               Sentences shared only between FDE and SA postings are kept: they are the evidence.

A low score means the posting's wording resembles SA postings. It is a lead for a person to read, not proof
that the title is wrong.

Run: uv run python -m q1_rebrand.explore_title_check [--quick: development snapshot only]
"""
import argparse
import json
from collections import defaultdict

import numpy as np
import pandas as pd

from pipeline.clean import _norm, remove_boilerplate, sentences
from pipeline.families import family

from . import protocol as P
from .data import current_postings, is_english, mask, posting_key, snapshot_dates
from .evaluate import _model, _splits, _vectorizer, cv_groups

CUTOFF = 0.4            # FDE postings scoring below this "read like SA" (same cut-off as the v2 analysis)
MIN_FDE = 5             # companies with fewer FDE postings are listed but not interpreted
TRAIN_CAP = 40          # postings per company per class in training, as in the protocol
C = 10.0                # fixed: the value the protocol's inner cross-validation chose most often
ROLE_FAMILIES = {"fde", "sa_ce"}


def drop_company_text(df: pd.DataFrame, min_docs: int = 3) -> tuple[pd.Series, pd.Series]:
    """Text without company-description sentences, and the share of characters removed, per posting."""
    out, removed = df.clean.copy(), pd.Series(0.0, index=df.index)
    for _, g in df.groupby("company"):
        split = {i: sentences(t) for i, t in g.clean.items()}
        docs, outside = defaultdict(int), set()
        for i, sents in split.items():
            for s in {_norm(x) for x in sents}:
                docs[s] += 1
                if g.family[i] not in ROLE_FAMILIES:
                    outside.add(s)
        company_text = {s for s, n in docs.items() if n >= min_docs and s in outside}
        for i, sents in split.items():
            kept = [s for s in sents if _norm(s) not in company_text]
            out.at[i] = " ".join(kept)
            total = sum(len(s) for s in sents)
            removed.at[i] = 1 - sum(len(s) for s in kept) / total if total else 0.0
    return out, removed


def corpus(dates: list[str], p: dict, variant: str) -> pd.DataFrame:
    df = current_postings(dates).reset_index(drop=True)
    df["family"] = df.title.map(family)
    bp = p["boilerplate"]
    df["clean"] = remove_boilerplate(df, "text", ("company", "source"), bp["share"], bp["min_docs"])
    df["removed"] = 0.0
    if variant == "no_company":
        df["clean"], df["removed"] = drop_company_text(df)
    df = df[df.family.isin(ROLE_FAMILIES)]
    df = df[df.clean.str.len() >= p["min_chars"]]
    df = df[df.clean.map(is_english)]
    df = df.assign(masked=df.clean.map(mask))
    df["key"] = [posting_key(c, m) for c, m in zip(df.company, df.masked, strict=True)]
    return df.sort_values("observed").drop_duplicates("key", keep="first").reset_index(drop=True)


def score(df: pd.DataFrame, p: dict, seed: int) -> pd.DataFrame:
    """P(FDE) for every posting from a model trained on other companies (capped per company and class)."""
    rng = np.random.default_rng(seed)
    y = (df.family == "fde").astype(int).to_numpy()
    groups = cv_groups(df, p["near_duplicate_cosine"])
    prob = np.full(len(df), np.nan)
    for train, test in _splits(groups, p["outer_folds"]):
        tr = df.iloc[train]
        keep = np.concatenate([g.sample(min(TRAIN_CAP, len(g)), random_state=int(rng.integers(2**31))).index.to_numpy()
                               for _, g in tr.groupby(["company", "family"])])
        vec = _vectorizer(p)
        model = _model(C).fit(vec.fit_transform(df.masked.loc[keep]), y[keep])
        prob[test] = model.predict_proba(vec.transform(df.masked.iloc[test]))[:, 1]
    return df.assign(p_fde=prob)


def by_company(scored: pd.DataFrame) -> pd.DataFrame:
    fde = scored[scored.family == "fde"]
    t = fde.groupby("company").agg(n_fde=("p_fde", "size"), mean_p=("p_fde", "mean"),
                                   sa_like=("p_fde", lambda x: float((x < CUTOFF).mean())),
                                   removed=("removed", "mean"))
    return t.round(3)


def summary(scored: pd.DataFrame) -> dict:
    fde, sa = scored[scored.family == "fde"], scored[scored.family == "sa_ce"]
    return {"n_fde": int(len(fde)), "n_sa": int(len(sa)), "companies": int(scored.company.nunique()),
            "fde_sa_like_share": round(float((fde.p_fde < CUTOFF).mean()), 3),
            "sa_fde_like_share": round(float((sa.p_fde > 1 - CUTOFF).mean()), 3),
            "balanced_accuracy": round(float(((fde.p_fde >= 0.5).mean() + (sa.p_fde < 0.5).mean()) / 2), 3)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="development snapshot only")
    args = ap.parse_args(argv)
    p = P.load()
    dates = snapshot_dates()
    if args.quick:
        dates = dates[:1]
    out, tables = {"status": "exploratory, outside the frozen protocol", "snapshots": dates, "cutoff": CUTOFF}, {}
    for variant in ("frozen", "no_company"):
        df = corpus(dates, p, variant)
        scored = score(df, p, p["seed"])
        out[variant] = summary(scored)
        tables[variant] = by_company(scored)
        print(f"{variant:11} {out[variant]}", flush=True)
        scored.drop(columns=["text", "clean"]).to_pickle(P.results_dir() / f"title_check_{variant}.pkl")
    t = tables["frozen"].merge(tables["no_company"], how="outer", left_index=True, right_index=True,
                               suffixes=("_frozen", "_noco"))
    t = t[["n_fde_frozen", "sa_like_frozen", "n_fde_noco", "sa_like_noco", "mean_p_noco", "removed_noco"]]
    t = t.sort_values("sa_like_noco", ascending=False)
    print(f"\nFDE postings scoring below {CUTOFF} (read like SA), companies with {MIN_FDE}+ FDE postings:")
    print(t[t.n_fde_noco >= MIN_FDE].to_string())
    out["by_company"] = json.loads(t.reset_index().to_json(orient="records"))
    path = P.results_dir() / ("title_check_quick.json" if args.quick else "title_check.json")
    path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
