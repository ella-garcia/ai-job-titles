"""Q1 / Q8 over time: has FDE moved away from Solutions Architect since Palantir's early postings?

Two measures, on archived postings (Wayback) and current postings:

1. SA-likeness score. Train the FDE-vs-SA classifier on current postings (the within-company headline
   sample, C chosen by nested CV). Score every archived FDE and SA posting with P(FDE). If FDE postings
   from 2011-22 score lower (more SA-like) than today's, FDE has moved away from SA. Archived SA postings
   are the control: if they shift as well, it is vocabulary of the era rather than the role.
   Current postings use their out-of-fold scores, so no posting is scored by a model trained on it.

2. Distance. Cosine similarity between the FDE and SA centroids per period, in one TF-IDF space fitted on
   all periods, with a company-cluster bootstrap interval. Only periods with both roles are reported.

Status: exploratory. Archived postings come from a few companies per period (see `companies`), so a
period's number can reflect who was archived as much as how the role changed.

Run: make q1-over-time
"""
import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from . import protocol as P
from .data import archive_postings, current_postings, prepare, snapshot_dates
from .evaluate import _model, _vectorizer, balanced, cv_groups, nested_cv


def cluster_mean_ci(values: np.ndarray, clusters: np.ndarray, n: int, rng) -> list[float] | None:
    """95% interval from resampling whole companies; None with fewer than 2 companies (no spread to resample)."""
    ids = np.unique(clusters)
    if len(ids) < 2:
        return None
    members = {c: np.flatnonzero(clusters == c) for c in ids}
    boots = [values[np.concatenate([members[c] for c in rng.choice(ids, len(ids))])].mean() for _ in range(n)]
    return [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)]


def sa_likeness(corpus: pd.DataFrame, p: dict, rng) -> pd.DataFrame:
    spec = p["tests"]["headline"]
    current = corpus[corpus.source != "wayback"]
    train = balanced(current, "family", "fde", "sa_ce", True, p["per_company_cap"], p["min_per_class"], rng)
    if train.company.nunique() < 2:
        raise SystemExit("Not enough current postings to train the FDE-vs-SA model.")
    y = (train.family == spec["positive"]).astype(int).to_numpy()
    cv = nested_cv(train.masked, y, cv_groups(train, p["near_duplicate_cosine"]), p)
    c = float(np.median(cv["chosen_c"]))
    vec = _vectorizer(p)
    model = _model(c).fit(vec.fit_transform(train.masked), y)

    scored = corpus[corpus.family.isin(["fde", "sa_ce"])].copy()
    scored["p_fde"] = model.predict_proba(vec.transform(scored.masked))[:, 1]
    oof = pd.Series(cv["prob"], index=train.key)           # out-of-fold scores for training postings
    in_train = scored.key.isin(oof.index)
    scored.loc[in_train, "p_fde"] = scored.loc[in_train, "key"].map(oof)
    scored["era"] = np.where(scored.source == "wayback", "archived", "current")
    rows = []
    for (era, period, fam), g in scored.groupby(["era", "period", "family"]):
        rows.append({"era": era, "period": period, "family": fam, "n": len(g), "companies": sorted(g.company.unique()),
                     "mean_p_fde": round(float(g.p_fde.mean()), 3),
                     "ci95": cluster_mean_ci(g.p_fde.to_numpy(), g.company.to_numpy(), p["bootstrap"], rng)})
    by_company = []
    archived = set(scored.loc[scored.era == "archived", "company"])
    for (company, era, period, fam), g in scored[scored.company.isin(archived)].groupby(
            ["company", "era", "period", "family"]):
        by_company.append({"company": company, "era": era, "period": period, "family": fam, "n": len(g),
                           "mean_p_fde": round(float(g.p_fde.mean()), 3)})
    return pd.DataFrame(rows), pd.DataFrame(by_company), c


def centroid_similarity(corpus: pd.DataFrame, p: dict, rng) -> pd.DataFrame:
    data = corpus[corpus.family.isin(["fde", "sa_ce"])]
    vec = TfidfVectorizer(min_df=3, sublinear_tf=True, stop_words="english").fit(data.masked)
    x = normalize(vec.transform(data.masked))
    rows = []
    for period, idx in data.groupby("period").indices.items():
        sub = data.iloc[idx]
        fde, sa = np.flatnonzero(sub.family.values == "fde"), np.flatnonzero(sub.family.values == "sa_ce")
        if len(fde) < 5 or len(sa) < 5:
            continue
        xs, comp = x[idx], sub.company.to_numpy()

        def sim(f, s, xs=xs):
            a, b = np.asarray(xs[f].mean(axis=0)).ravel(), np.asarray(xs[s].mean(axis=0)).ravel()
            return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

        boots = []
        f_ids, s_ids = np.unique(comp[fde]), np.unique(comp[sa])
        for _ in range(p["bootstrap"] // 4):
            f = np.concatenate([fde[comp[fde] == c] for c in rng.choice(f_ids, len(f_ids))])
            s = np.concatenate([sa[comp[sa] == c] for c in rng.choice(s_ids, len(s_ids))])
            boots.append(sim(f, s))
        # Note: resampling companies (with duplicates) makes the centroids noisier, which biases the
        # bootstrap similarity downward; the point estimate can sit above the interval. Read the median too.
        rows.append({"period": period, "n_fde": len(fde), "n_sa": len(sa),
                     "fde_companies": sorted(f_ids), "sa_companies": sorted(s_ids),
                     "cosine_fde_sa": round(sim(fde, sa), 3),
                     "bootstrap_median": round(float(np.median(boots)), 3),
                     "ci95": [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)]})
    return pd.DataFrame(rows)


def main() -> None:
    p = P.load()
    rng = np.random.default_rng(p["seed"])
    frozen = P.frozen()
    dates = [d for d in snapshot_dates() if not frozen or d <= frozen["frozen_at"]]
    raw = pd.concat([current_postings(dates), archive_postings()], ignore_index=True)
    corpus = prepare(raw, p)
    print(f"{len(corpus):,} postings: {int((corpus.source == 'wayback').sum()):,} archived, "
          f"{int((corpus.source != 'wayback').sum()):,} current")
    likeness, by_company, c = sa_likeness(corpus, p, rng)
    distance = centroid_similarity(corpus, p, rng)
    out = P.results_dir()
    likeness.to_csv(out / "over_time_sa_likeness.csv", index=False)
    by_company.to_csv(out / "over_time_by_company.csv", index=False)
    distance.to_csv(out / "over_time_distance.csv", index=False)
    (out / "over_time.json").write_text(json.dumps(
        {"status": "exploratory", "model_c": c, "sa_likeness": likeness.to_dict("records"),
         "by_company": by_company.to_dict("records"),
         "distance": distance.to_dict("records")}, indent=2, default=str))
    pd.set_option("display.width", 200)
    print("\nMean P(FDE) by period (1 = reads like an FDE posting, 0 = like an SA posting):")
    print(likeness[["era", "period", "family", "n", "mean_p_fde", "ci95", "companies"]].to_string(index=False))
    if len(by_company):
        print("\nSame companies then and now (companies with archived postings):")
        print(by_company.to_string(index=False))
    if len(distance):
        print("\nCosine similarity of FDE and SA centroids by period (higher = more alike):")
        print(distance[["period", "n_fde", "n_sa", "cosine_fde_sa", "bootstrap_median", "ci95"]].to_string(index=False))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
