"""Q1 evaluation engine: balanced sampling, nested group cross-validation, cluster bootstrap,
permutation baseline, stable terms and Holm-corrected comparisons. All settings come from protocol.yaml.
"""
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import normalize

# --- Sampling -------------------------------------------------------------------------------------

def balanced(df: pd.DataFrame, label: str, positive: str, negative: str, within_company: bool,
             cap: int, min_per_class: int, rng: np.random.Generator) -> pd.DataFrame:
    """Cap each company per class. Within-company: keep companies posting both classes (at least
    `min_per_class` each) and take equal numbers of each from every company. Otherwise equalise overall."""
    df = df[df[label].isin([positive, negative])]
    parts = []
    for _, g in df.groupby("company"):
        counts = g[label].value_counts()
        if within_company:
            if min(counts.get(positive, 0), counts.get(negative, 0)) < min_per_class:
                continue
            n = min(cap, counts[positive], counts[negative])
            caps = {positive: n, negative: n}
        else:
            caps = {c: min(cap, counts.get(c, 0)) for c in (positive, negative)}
        for c, n in caps.items():
            if n:
                parts.append(g[g[label] == c].sample(n, random_state=int(rng.integers(2**31))))
    if not parts:
        return df.iloc[0:0]
    out = pd.concat(parts)
    if not within_company:
        n = out[label].value_counts().reindex([positive, negative], fill_value=0).min()
        if n == 0:
            return df.iloc[0:0]
        out = out.groupby(label, group_keys=False).sample(n, random_state=int(rng.integers(2**31)))
    return out.reset_index(drop=True)


def cv_groups(df: pd.DataFrame, threshold: float) -> np.ndarray:
    """Group ids for cross-validation and bootstrap: company, merged with any near-duplicate posting
    (cosine >= threshold on word TF-IDF), so near-identical text never sits on both sides of a split."""
    n = len(df)
    if n == 0:
        return np.array([], dtype=int)
    x = normalize(TfidfVectorizer(min_df=1, sublinear_tf=True).fit_transform(df.masked))
    near = (x @ x.T).toarray() >= threshold
    codes = pd.factorize(df.company)[0]
    same_company = codes[:, None] == codes[None, :]
    _, labels = connected_components(near | same_company, directed=False)
    return labels


# --- Cross-validation -----------------------------------------------------------------------------

def _vectorizer(p: dict) -> TfidfVectorizer:
    t = p["tfidf"]
    return TfidfVectorizer(ngram_range=(t["ngram_min"], t["ngram_max"]), min_df=t["min_df"],
                           sublinear_tf=t["sublinear_tf"], stop_words="english")


def _model(c: float) -> LogisticRegression:
    return LogisticRegression(C=c, max_iter=3000, class_weight="balanced")


def _splits(groups: np.ndarray, k: int):
    n_groups = len(np.unique(groups))
    if n_groups < 2:
        return []
    return list(GroupKFold(n_splits=min(k, n_groups)).split(np.zeros(len(groups)), groups=groups))


def nested_cv(texts: pd.Series, y: np.ndarray, groups: np.ndarray, p: dict) -> dict:
    """Outer GroupKFold for scoring; C chosen on inner GroupKFold within each training part.
    The vectorizer is fitted on training text only, inside every split."""
    pred, prob = np.full(len(y), -1), np.full(len(y), np.nan)
    chosen, coefs, folds = [], [], []
    for train, test in _splits(groups, p["outer_folds"]):
        best_c, best_acc = p["c_grid"][0], -1.0
        inner = _splits(groups[train], p["inner_folds"])
        if inner:
            for c in p["c_grid"]:
                hits = 0
                for itr, ite in inner:
                    tr, te = train[itr], train[ite]
                    if len(np.unique(y[tr])) < 2:
                        continue
                    vec = _vectorizer(p)
                    m = _model(c).fit(vec.fit_transform(texts.iloc[tr]), y[tr])
                    hits += (m.predict(vec.transform(texts.iloc[te])) == y[te]).sum()
                acc = hits / len(train)
                if acc > best_acc:
                    best_c, best_acc = c, acc
        vec = _vectorizer(p)
        x_train, x_test = vec.fit_transform(texts.iloc[train]), vec.transform(texts.iloc[test])
        m = _model(best_c).fit(x_train, y[train])
        pred[test], prob[test] = m.predict(x_test), m.predict_proba(x_test)[:, 1]
        chosen.append(best_c)
        coefs.append(pd.Series(m.coef_[0], index=vec.get_feature_names_out()))
        folds.append((train, test, x_train, x_test))
    return {"pred": pred, "prob": prob, "chosen_c": chosen, "coefs": coefs, "folds": folds}


def permutation_null(y: np.ndarray, folds: list, c: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Accuracy with shuffled labels, reusing each fold's fitted features (labels don't affect them)."""
    out = []
    for _ in range(n):
        yp, pred = rng.permutation(y), np.full(len(y), -1)
        for train, test, x_train, x_test in folds:
            if len(np.unique(yp[train])) < 2:
                pred[test] = yp[train][0]
                continue
            pred[test] = _model(c).fit(x_train, yp[train]).predict(x_test)
        out.append(accuracy_score(yp, pred))
    return np.array(out)


def cluster_bootstrap(y: np.ndarray, pred: np.ndarray, groups: np.ndarray, n: int,
                      rng: np.random.Generator) -> np.ndarray:
    """Accuracy over `n` resamples of whole groups (clusters) with replacement."""
    ids = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in ids}
    correct = (y == pred).astype(float)
    out = np.empty(n)
    for b in range(n):
        idx = np.concatenate([members[g] for g in rng.choice(ids, size=len(ids), replace=True)])
        out[b] = correct[idx].mean()
    return out


def stable_terms(coefs: list[pd.Series], k: int, min_folds: int) -> dict:
    """Terms among the top-k (each direction) in at least `min_folds` folds, ordered by mean weight."""
    def stable(sign):
        tops = [set((s * sign).nlargest(k).index) for s in coefs]
        counts = pd.Series([t for top in tops for t in top]).value_counts()
        keep = counts[counts >= min_folds].index
        mean = pd.concat(coefs, axis=1).reindex(keep).mean(axis=1) * sign
        return mean.sort_values(ascending=False).index.tolist()
    return {"positive": stable(1), "negative": stable(-1)}


# --- Tests and comparisons ------------------------------------------------------------------------

def run_test(df: pd.DataFrame, spec: dict, p: dict, seed: int, full: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    sample = balanced(df, spec["label"], spec["positive"], spec["negative"], spec["within_company"],
                      p["per_company_cap"], p["min_per_class"], rng)
    if sample.empty or sample.company.nunique() < 2:
        return {"error": "not enough data (needs 2+ companies with both classes)", "n": int(len(sample))}
    y = (sample[spec["label"]] == spec["positive"]).astype(int).to_numpy()
    groups = cv_groups(sample, p["near_duplicate_cosine"])
    cv = nested_cv(sample.masked, y, groups, p)
    ok = cv["pred"] >= 0
    result = {
        "n": int(ok.sum()), "n_positive": int(y[ok].sum()), "companies": sorted(sample.company.unique().tolist()),
        "cv_groups": int(len(np.unique(groups))), "chosen_c": cv["chosen_c"],
        "accuracy": round(float(accuracy_score(y[ok], cv["pred"][ok])), 3),
        "macro_f1": round(float(f1_score(y[ok], cv["pred"][ok], average="macro")), 3),
    }
    if not full:
        return result
    boot = cluster_bootstrap(y[ok], cv["pred"][ok], groups[ok], p["bootstrap"], rng)
    c_mid = float(np.median(cv["chosen_c"]))
    null = permutation_null(y, cv["folds"], c_mid, p["permutations"], rng)
    result.update({
        "ci95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
        "chance_mean": round(float(null.mean()), 3), "chance_95th": round(float(np.percentile(null, 95)), 3),
        "p_vs_chance": round(float((1 + (null >= result["accuracy"]).sum()) / (1 + len(null))), 4),
        "terms": stable_terms(cv["coefs"], p["top_terms"]["k"], p["top_terms"]["min_folds"]),
        "_boot": boot,
    })
    return result


def holm(pvalues: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the original order."""
    m = len(pvalues)
    order = np.argsort(pvalues)
    adjusted, running = np.empty(m), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted.tolist()


def compare(results: dict, comparisons: list) -> list[dict]:
    """One-sided comparisons between tests from their (independent) cluster-bootstrap distributions."""
    rows = []
    for a, b, direction in comparisons:
        if "_boot" not in results.get(a, {}) or "_boot" not in results.get(b, {}):
            rows.append({"a": a, "b": b, "direction": direction, "error": "missing test"})
            continue
        diff = results[a]["_boot"] - results[b]["_boot"]
        p = float((diff <= 0).mean()) if direction == "greater" else float((diff >= 0).mean())
        rows.append({"a": a, "b": b, "direction": direction,
                     "difference": round(results[a]["accuracy"] - results[b]["accuracy"], 3),
                     "ci95": [round(float(np.percentile(diff, 2.5)), 3), round(float(np.percentile(diff, 97.5)), 3)],
                     "p": round(max(p, 1 / len(diff)), 4)})
    valid = [r for r in rows if "p" in r]
    for r, adj in zip(valid, holm([r["p"] for r in valid]), strict=True):
        r["p_holm"] = round(adj, 4)
    return rows


def run_suite(corpus: pd.DataFrame, p: dict) -> dict:
    results = {name: run_test(corpus, spec, p, p["seed"]) for name, spec in p["tests"].items()}
    comparisons = compare(results, p["comparisons"])
    head = p["tests"]["headline"]
    seeds = [run_test(corpus, head, p, p["seed"] + s, full=False).get("accuracy") for s in range(p["seeds"])]
    seeds = [s for s in seeds if s is not None]
    for r in results.values():
        r.pop("_boot", None)
    return {"tests": results, "comparisons": comparisons,
            "headline_over_seeds": {"accuracies": seeds,
                                    "mean": round(float(np.mean(seeds)), 3) if seeds else None,
                                    "sd": round(float(np.std(seeds)), 3) if seeds else None}}
