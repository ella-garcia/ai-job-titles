"""Q1 protocol: sampling, grouping, cross-validation, uncertainty and the freeze guard rails."""
import json

import numpy as np
import pandas as pd
import pytest

from q1_rebrand import evaluate as E
from q1_rebrand import final
from q1_rebrand import protocol as P

PROTOCOL = {"tfidf": {"ngram_min": 1, "ngram_max": 1, "min_df": 1, "sublinear_tf": True},
            "c_grid": [0.1, 1.0], "outer_folds": 3, "inner_folds": 2}

FDE_WORDS = "build deploy production systems customer site agents ship code"
SA_WORDS = "presales workshops demos account presentations architecture proposals"


def synthetic(n_companies=4, per_class=10, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(n_companies):
        for i in range(per_class):
            for fam, words in (("fde", FDE_WORDS), ("sa_ce", SA_WORDS)):
                w = rng.choice(words.split(), size=8).tolist() + [f"company{c}", f"post{c}x{i}x{fam}"]
                rows.append({"company": f"co{c}", "family": fam, "masked": " ".join(w)})
    return pd.DataFrame(rows)


def test_balanced_within_company_equal_per_company():
    df = synthetic()
    df = pd.concat([df, df[df.company == "co0"].assign(company="onlyfde").query("family == 'fde'")])
    s = E.balanced(df, "family", "fde", "sa_ce", True, cap=5, min_per_class=3, rng=np.random.default_rng(0))
    assert "onlyfde" not in set(s.company)                       # posts only one role: excluded
    counts = s.groupby(["company", "family"]).size()
    assert (counts == 5).all()


def test_cv_groups_merge_near_duplicates_across_companies():
    same = "deploy agents in production for customers"
    df = pd.DataFrame({"company": ["a", "b", "c"], "masked": [same, same, "run presales workshops and demos"]})
    g = E.cv_groups(df, 0.95)
    assert g[0] == g[1] != g[2]


def test_nested_cv_separates_distinct_vocabularies():
    df = synthetic()
    y = (df.family == "fde").astype(int).to_numpy()
    cv = E.nested_cv(df.masked, y, pd.factorize(df.company)[0], PROTOCOL)
    assert (cv["pred"] == y).mean() > 0.9
    assert all(c in PROTOCOL["c_grid"] for c in cv["chosen_c"])
    null = E.permutation_null(y, cv["folds"], 1.0, 30, np.random.default_rng(0))
    assert 0.3 < null.mean() < 0.7


def test_cluster_bootstrap_resamples_whole_groups():
    y = np.array([1, 1, 0, 0])
    pred = np.array([1, 1, 1, 1])                                 # group 0 all right, group 1 all wrong
    boot = E.cluster_bootstrap(y, pred, np.array([0, 0, 1, 1]), 500, np.random.default_rng(0))
    assert set(np.round(boot, 2)) <= {0.0, 0.5, 1.0}


def test_holm():
    assert E.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_final_refuses_without_freeze_or_after_protocol_change(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "FROZEN", tmp_path / "frozen_config.json")
    with pytest.raises(SystemExit, match="Not frozen"):
        final.main([])
    P.FROZEN.write_text(json.dumps({"protocol_hash": "something-else", "frozen_at": "2026-11-13"}))
    with pytest.raises(SystemExit, match="changed since freezing"):
        final.main([])


def test_over_time_interval_needs_two_companies():
    from q1_rebrand.over_time import cluster_mean_ci
    rng = np.random.default_rng(0)
    assert cluster_mean_ci(np.array([0.2, 0.4]), np.array(["a", "a"]), 100, rng) is None
    ci = cluster_mean_ci(np.array([0.2, 0.4, 0.6, 0.8]), np.array(["a", "a", "b", "b"]), 500, rng)
    assert ci[0] <= 0.5 <= ci[1]
