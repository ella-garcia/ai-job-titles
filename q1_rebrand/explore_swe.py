"""Exploratory Q1 tests against engineering roles (spec: docs/specs/explore_swe_spec.md).

Is FDE a new job (R1), software engineering placed with the customer (R2), or a hybrid of SA and software
engineering (R3)? Outside the frozen protocol: the new title groups and extra masking live in this file, so
the protocol hash is unchanged.

E1  FDE vs software engineer (SWE): all companies, and same companies
E2  SA vs SWE: scale check
E3  FDE vs ML / AI engineer
E4  Placement: a five-way model (SA, SWE, ML, support, consultant) trained without FDE postings scores
    every FDE posting out of company; SA postings are the control
E5  FDE vs SA with and without strategist titles
E6  Strategist titles (Deployment / Forward Deployed Strategist) against SA and against FDE engineer titles

The reading rules in READING_RULES are written to the output. The E4 rule was switched from mean
probabilities to top-class shares on 27 Nov, after the development and 19-25 Nov runs and before the freeze.
`--freeze` records a hash of the spec, the title rules, the masking and the reading rules, plus the keys of
every posting seen so far; `--confirm` then runs on postings first seen after the freeze and refuses if
anything hashed has changed.

Run: uv run python -m q1_rebrand.explore_swe [--quick] [--all | --dates 2026-11-13 ... | --freeze | --confirm]
     Default data: the development set (snapshots up to the freeze). --all uses every snapshot and writes
     explore_swe_all.json.
"""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from . import protocol as P
from .data import current_postings, prepare, snapshot_dates
from .evaluate import _splits, _vectorizer, compare, cv_groups, run_test
from .explore_titles import INTERNAL_IT, SUPPORT_TITLE, SUPPORT_WORDS
from .run import development_corpus

SPEC = Path(__file__).resolve().parents[1] / "docs" / "specs" / "explore_swe_spec.md"

# --- Title groups (spec section 2): applied after the existing rules, so no posting changes group ----------
SWE_INCLUDE = re.compile(r"software (?:engineer|developer)|back[- ]?end engineer|front[- ]?end engineer|"
                         r"full[- ]?stack engineer|platform engineer|infrastructure engineer", re.I)
CUSTOMER_FACING = r"forward[- ]deployed|solutions?|sales|customer|field|support|deployment|implementation|success"
MANAGEMENT = r"manager|director|head of|\bvp\b|\blead\b"
JUNIOR = r"\bintern\b|internship|graduate|new grad"
SWE_EXCLUDE = re.compile(f"{CUSTOMER_FACING}|{MANAGEMENT}|{JUNIOR}|machine learning|\\bml\\b|\\bai\\b|\\bdata\\b", re.I)
ML_INCLUDE = re.compile(r"machine learning engineer|\bml engineer|\bai engineer|applied scientist", re.I)
# "the SWE exclusions" for the ML group: the customer-facing, management and junior words (not ML / AI / data)
ML_EXCLUDE = re.compile(f"applied ai engineer|research scientist|{CUSTOMER_FACING}|{MANAGEMENT}|{JUNIOR}", re.I)
APPLIED_AI = re.compile(r"applied ai engineer", re.I)
STRATEGIST = re.compile(r"strateg", re.I)
SENIOR = re.compile(r"\b(?:senior|sr\.?|staff|principal)\b", re.I)

# Extra masking (spec section 2): the new title phrases, on top of the frozen masking.
EXTRA_MASK = re.compile(
    r"(software|machine learning|\bml|\bai) (engineer|developer)\w*|applied scientist\w*|"
    r"back[- ]?end|front[- ]?end|full[- ]?stack|(platform|infrastructure) engineer\w*|\bswes?\b|\bmles?\b|"
    r"\bstrategists?\b", re.I)   # bare "strategist": the frozen list masks only "deployment strateg..."

NEIGHBOURS = ["sa", "swe", "ml", "support", "consultant"]

READING_RULES = {
    "note": "Proposed in the spec before any run; not pre-registered.",
    "E1": ["FDE vs SWE <= 0.65: R2, SWE is FDE's nearest neighbour",
           "FDE vs SWE >= 0.85 and above FDE vs SA on the same scope: R1 for SWE",
           "between: decided by E4"],
    "E4 (share of FDE postings whose highest probability is each class; switched from mean probabilities "
    "on 27 Nov, before the freeze)": [
        "top(SWE) >= 0.60: R2", "top(SA) >= 0.60: rebrand reading (check labels first)",
        "top(SA) >= 0.25 and top(SWE) >= 0.25 and top(SA) + top(SWE) >= 0.70: R3, hybrid of SA and SWE",
        "no class >= 0.40: R1, FDE sits away from all five neighbours", "anything else: unresolved",
        "mean probabilities are reported alongside but do not decide the reading"],
    "E5": "if dropping strategists moves all-companies accuracy by more than 0.04, report both and discuss",
    "E6": "added after the first runs, no reading rule; a same-company test that predicts one class (0.500) "
          "is a non-result",
}


def label(corpus: pd.DataFrame) -> pd.DataFrame:
    """Adds xgroup (fde, sa, consultant, pm, support, swe, ml, applied_ai, other) and masks the new title phrases."""
    title = corpus.title.fillna("")
    free = corpus.family.isin(["other", "ai_eng"])          # not already in a tested family
    support = free & title.str.contains(SUPPORT_TITLE) & ~title.str.contains(INTERNAL_IT)
    applied = free & ~support & title.str.contains(APPLIED_AI)
    ml = free & ~support & ~applied & title.str.contains(ML_INCLUDE) & ~title.str.contains(ML_EXCLUDE)
    swe = free & ~support & ~ml & ~applied & title.str.contains(SWE_INCLUDE) & ~title.str.contains(SWE_EXCLUDE)
    g = np.select([corpus.family == "fde", corpus.family == "sa_ce", corpus.family == "tech_consultant",
                   corpus.family == "pm", support, applied, ml, swe],
                  ["fde", "sa", "consultant", "pm", "support", "applied_ai", "ml", "swe"], default="other")
    out = corpus.assign(xgroup=g)
    out["fde_kind"] = np.where(out.xgroup != "fde", out.xgroup,
                               np.where(title.str.contains(STRATEGIST), "fde_strategist", "fde_engineer"))
    out["masked"] = (out.masked.str.replace(SUPPORT_WORDS, " ", regex=True)
                     .str.replace(EXTRA_MASK, " ", regex=True).str.replace(r"\s+", " ", regex=True))
    assert not out.masked.str.contains(r"forward[- ]deployed", case=False).any(), "FDE masking failed"
    return out


def counts(c: pd.DataFrame) -> dict:
    per_company = (c[c.xgroup != "other"].groupby(["company", "xgroup"]).size().unstack(fill_value=0))
    senior = {g: round(float(c[c.xgroup == g].title.fillna("").str.contains(SENIOR).mean()), 3)
              for g in ("fde", "swe")}
    return {"postings": c.xgroup.value_counts().to_dict(),
            "companies": c.groupby("xgroup").company.nunique().to_dict(),
            "strategist_fde": int((c.fde_kind == "fde_strategist").sum()), "senior_share": senior,
            "applied_ai_by_company": c[c.xgroup == "applied_ai"].company.value_counts().to_dict(),
            "per_company": json.loads(per_company.reset_index().to_json(orient="records"))}


# --- E1, E2, E3, E5: the frozen binary procedure on the new groups -----------------------------------------

BINARY = {
    "E1_fde_vs_swe_all":   ("xgroup", "fde", "swe", False),
    "E1_fde_vs_swe_same":  ("xgroup", "fde", "swe", True),
    "E2_sa_vs_swe_all":    ("xgroup", "sa", "swe", False),
    "E3_fde_vs_ml_all":    ("xgroup", "fde", "ml", False),
    "E5_fde_vs_sa_all":            ("xgroup", "fde", "sa", False),
    "E5_fde_vs_sa_same":           ("xgroup", "fde", "sa", True),
    "E5_fde_vs_sa_all_no_strat":   ("fde_kind", "fde_engineer", "sa", False),
    "E5_fde_vs_sa_same_no_strat":  ("fde_kind", "fde_engineer", "sa", True),
    "E6_strat_vs_sa_all":          ("fde_kind", "fde_strategist", "sa", False),
    "E6_strat_vs_sa_same":         ("fde_kind", "fde_strategist", "sa", True),
    "E6_strat_vs_eng_all":         ("fde_kind", "fde_strategist", "fde_engineer", False),
    "E6_strat_vs_eng_same":        ("fde_kind", "fde_strategist", "fde_engineer", True),
}
# E6 compares strategists with FDE engineers against SA; E5_*_no_strat is the FDE engineer vs SA test.
E6_COMPARISONS = [["E6_strat_vs_sa_all", "E5_fde_vs_sa_all_no_strat", "less"],
                  ["E6_strat_vs_sa_same", "E5_fde_vs_sa_same_no_strat", "less"]]


SENIOR_GAP = 0.20      # spec section 6: rerun E1 on senior titles if the senior shares differ by more than this
SENIOR_TESTS = {"E1_senior_fde_vs_swe_all":  ("xgroup", "fde", "swe", False),
                "E1_senior_fde_vs_swe_same": ("xgroup", "fde", "swe", True)}


def binary_tests(c: pd.DataFrame, p: dict, quick: bool, tests: dict = BINARY) -> dict:
    out = {}
    for name, (col, pos, neg, within) in tests.items():
        spec = {"label": col, "positive": pos, "negative": neg, "within_company": within}
        r = run_test(c, spec, p, p["seed"], full=not quick)
        if "error" not in r:
            seeds = [run_test(c, spec, p, p["seed"] + s, full=False).get("accuracy")
                     for s in range(1 if quick else p["seeds"])]
            seeds = [s for s in seeds if s is not None]
            r["seeds"] = {"mean": round(float(np.mean(seeds)), 3), "sd": round(float(np.std(seeds)), 3)}
        out[name] = r
        print(f"{name:28} " + (r["error"] if "error" in r else
              f"n={r['n']:4} cos={len(r['companies']):2} acc={r['accuracy']:.3f} CI={r.get('ci95')} "
              f"chance95={r.get('chance_95th')} seeds={r['seeds']}"), flush=True)
    return out


# --- E4: placement among neighbours ------------------------------------------------------------------------

def _fit(c_value: float, x, y) -> LogisticRegression:
    return LogisticRegression(C=c_value, max_iter=3000, class_weight="balanced").fit(x, y)


def placement(c: pd.DataFrame, p: dict, target: str, quick: bool) -> dict:
    """Mean class probabilities for `target` postings from a model trained on the neighbour classes at other
    companies. For the SA control, SA is a training class and SA postings are scored out of fold."""
    rng = np.random.default_rng(p["seed"])
    eligible = c[c.xgroup.isin(NEIGHBOURS)].groupby(["xgroup", "company"]).size()
    enough = (eligible.get("consultant", pd.Series(dtype=int)) >= p["min_per_class"]).sum() >= 4
    classes = [g for g in NEIGHBOURS if g != "consultant" or enough]      # spec: only consultant is conditional
    dropped = [g for g in NEIGHBOURS if g not in classes]
    train_pool = pd.concat([g.sample(min(p["per_company_cap"], len(g)), random_state=int(rng.integers(2**31)))
                            for _, g in c[c.xgroup.isin(classes)].groupby(["company", "xgroup"])])
    targets = c[c.xgroup == target] if target not in classes else train_pool[train_pool.xgroup == target]
    both = pd.concat([train_pool, targets[~targets.index.isin(train_pool.index)]])
    groups = pd.Series(cv_groups(both, p["near_duplicate_cosine"]), index=both.index)
    prob = pd.DataFrame(np.nan, index=targets.index, columns=classes)
    for train, test in _splits(groups.to_numpy(), p["outer_folds"]):
        tr = both.iloc[train]
        tr = tr[tr.index.isin(train_pool.index)]
        te = both.iloc[test]
        te = te[te.index.isin(targets.index)]
        if te.empty or tr.xgroup.nunique() < 2:
            continue
        best_c, best = p["c_grid"][0], -1.0
        inner = _splits(groups.loc[tr.index].to_numpy(), p["inner_folds"])
        for cval in ([10.0] if quick else p["c_grid"]):
            hits = 0
            for itr, ite in inner:
                a, b = tr.iloc[itr], tr.iloc[ite]
                if a.xgroup.nunique() < 2:
                    continue
                vec = _vectorizer(p)
                m = _fit(cval, vec.fit_transform(a.masked), a.xgroup)
                hits += (m.predict(vec.transform(b.masked)) == b.xgroup).sum()
            if hits > best:
                best_c, best = cval, hits
        vec = _vectorizer(p)
        m = _fit(best_c, vec.fit_transform(tr.masked), tr.xgroup)
        prob.loc[te.index, :] = 0.0                    # a class absent from this fold's training gets 0
        prob.loc[te.index, list(m.classes_)] = m.predict_proba(vec.transform(te.masked))
    prob = prob.dropna()
    company = targets.company.loc[prob.index]
    top = prob.idxmax(axis=1)
    cos = company.unique()
    draws_mean, draws_top = [], []
    by_co = {k: prob[company == k] for k in cos}
    for _ in range(200 if quick else p["bootstrap"]):
        sample = pd.concat([by_co[k] for k in rng.choice(cos, len(cos))])
        draws_mean.append(sample.mean())
        draws_top.append(sample.idxmax(axis=1).value_counts(normalize=True).reindex(classes, fill_value=0))
    dm, dt = pd.DataFrame(draws_mean), pd.DataFrame(draws_top)
    table = {k: {"mean_prob": round(float(prob[k].mean()), 3),
                 "mean_prob_ci95": [round(float(dm[k].quantile(0.025)), 3), round(float(dm[k].quantile(0.975)), 3)],
                 "top_share": round(float((top == k).mean()), 3),
                 "top_share_ci95": [round(float(dt[k].quantile(0.025)), 3), round(float(dt[k].quantile(0.975)), 3)]}
             for k in classes}
    return {"target": target, "n": int(len(prob)), "companies": int(len(cos)), "classes": classes,
            "dropped_classes": dropped, "table": table}


def read_e4(table: dict) -> str:
    m = {k: v["top_share"] for k, v in table.items()}
    sa, swe = m.get("sa", 0), m.get("swe", 0)
    if swe >= 0.60:
        return "R2: software engineering is FDE's home"
    if sa >= 0.60:
        return "rebrand reading: contradicts the main result, check labels first"
    if sa >= 0.25 and swe >= 0.25 and sa + swe >= 0.70:
        return "R3: hybrid of SA and SWE"
    if max(m.values()) < 0.40:
        return "R1: away from all neighbours"
    return "unresolved"


def read_e1(tests: dict) -> dict:
    out = {}
    for scope in ("all", "same"):
        swe = tests.get(f"E1_fde_vs_swe_{scope}", {}).get("accuracy")
        sa = tests.get(f"E5_fde_vs_sa_{scope}", {}).get("accuracy")
        if swe is None:
            out[scope] = "no result"
        elif swe <= 0.65:
            out[scope] = "R2"
        elif swe >= 0.85 and sa is not None and swe > sa:
            out[scope] = "R1 for SWE"
        else:
            out[scope] = "between: decided by E4"
    return out


# --- Freeze and confirmation (spec section 5) ---------------------------------------------------------------

SWE_FROZEN = P.FROZEN_DIR / "explore_swe_frozen.json"
SWE_KEYS = P.FROZEN_DIR / "explore_swe_seen_keys.txt"     # hashes of postings seen at the freeze, no text


def rules_hash() -> str:
    """Hash of the spec, the title rules, the masking, the tests and the reading rules, on top of the protocol."""
    rules = {"patterns": {k: v.pattern for k, v in {
                 "swe_include": SWE_INCLUDE, "swe_exclude": SWE_EXCLUDE, "ml_include": ML_INCLUDE,
                 "ml_exclude": ML_EXCLUDE, "applied_ai": APPLIED_AI, "strategist": STRATEGIST, "senior": SENIOR,
                 "extra_mask": EXTRA_MASK, "support_title": SUPPORT_TITLE, "internal_it": INTERNAL_IT,
                 "support_words": SUPPORT_WORDS}.items()},
             "neighbours": NEIGHBOURS, "binary": BINARY, "senior_tests": SENIOR_TESTS, "senior_gap": SENIOR_GAP,
             "e6_comparisons": E6_COMPARISONS, "reading_rules": READING_RULES, "protocol_hash": P.protocol_hash()}
    extra = json.dumps(rules, sort_keys=True, default=str).encode()
    return hashlib.sha256(SPEC.read_bytes() + b"\n" + extra).hexdigest()


def freeze(p: dict) -> None:
    if SWE_FROZEN.exists():
        raise SystemExit(f"Already frozen: {SWE_FROZEN}. Delete it only if --confirm has never been run.")
    if P.git("status", "--porcelain", "--", "q1_rebrand", "docs/specs", "pipeline", "config.yaml"):
        raise SystemExit("Commit explore_swe.py and the spec first: the freeze records the commit.")
    dates = snapshot_dates()
    seen = prepare(current_postings(dates), p)
    SWE_KEYS.write_text("\n".join(sorted(seen.key)) + "\n")
    config = {"rules_hash": rules_hash(), "git_commit": P.git("rev-parse", "HEAD"), "frozen_at": max(dates),
              "frozen_on": time.strftime("%Y-%m-%d"), "seen_snapshots": dates, "seen_postings": int(len(seen))}
    SWE_FROZEN.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps(config, indent=2))
    print(f"Frozen. Commit {SWE_FROZEN.name} and {SWE_KEYS.name}.")


def confirmation_corpus(p: dict) -> tuple[pd.DataFrame, list[str], dict]:
    from .final import held_out_corpus
    if not SWE_FROZEN.exists():
        raise SystemExit("Not frozen: run --freeze first.")
    frozen = json.loads(SWE_FROZEN.read_text())
    if rules_hash() != frozen["rules_hash"]:
        raise SystemExit("The spec, title rules, masking or reading rules changed since the freeze.")
    # postings first seen after the freeze, minus near-duplicates of anything seen at the freeze
    corpus, dates = held_out_corpus(p, {"frozen_at": frozen["frozen_at"], "dev_snapshots": frozen["seen_snapshots"]})
    seen = set(SWE_KEYS.read_text().split())
    return corpus[~corpus.key.isin(seen)].reset_index(drop=True), dates, frozen


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="accuracy only, one seed, short bootstrap")
    ap.add_argument("--dates", nargs="*", help="snapshot dates to use (default: the development set)")
    ap.add_argument("--all", action="store_true", help="every snapshot; writes explore_swe_all.json")
    ap.add_argument("--freeze", action="store_true", help="hash the rules and record every posting seen so far")
    ap.add_argument("--confirm", action="store_true", help="postings first seen after the freeze")
    args = ap.parse_args(argv)
    p = P.load()
    t0 = time.time()
    if args.freeze:
        return freeze(p)
    frozen = None
    if args.all:
        args.dates = snapshot_dates()
    if args.confirm:
        corpus, dates, frozen = confirmation_corpus(p)
    elif args.dates:
        corpus, dates = prepare(current_postings(args.dates), p), args.dates
    else:
        corpus, dates = development_corpus(p)
    c = label(corpus)
    out = {"status": "exploratory, outside the frozen protocol", "spec": str(SPEC.relative_to(SPEC.parents[2])),
           "spec_sha256": hashlib.sha256(SPEC.read_bytes()).hexdigest(), "reading_rules": READING_RULES,
           "protocol": p["version"], "git_commit": P.git("rev-parse", "HEAD"), "snapshots": dates,
           "counts": counts(c), "frozen": frozen}
    print(f"{len(c):,} postings from {dates}; groups: {out['counts']['postings']}", flush=True)
    print(f"senior share: {out['counts']['senior_share']}; "
          f"strategist FDE: {out['counts']['strategist_fde']}", flush=True)
    tests = binary_tests(c, p, args.quick)
    if not args.quick:
        out["comparisons"] = compare(tests, [["E1_fde_vs_swe_all", "E5_fde_vs_sa_all", "greater"],
                                             ["E1_fde_vs_swe_same", "E5_fde_vs_sa_same", "greater"],
                                             ["E2_sa_vs_swe_all", "E1_fde_vs_swe_all", "greater"]])
        for cmp in out["comparisons"]:
            if "p" in cmp:
                print(f"  {cmp['a']} > {cmp['b']}: diff {cmp['difference']:+.3f} {cmp['ci95']}, "
                      f"Holm p={cmp['p_holm']}", flush=True)
        out["E6_comparisons"] = compare(tests, E6_COMPARISONS)      # a separate Holm family
        for cmp in out["E6_comparisons"]:
            if "p" in cmp:
                print(f"  {cmp['a']} < {cmp['b']}: diff {cmp['difference']:+.3f} {cmp['ci95']}, "
                      f"Holm p={cmp['p_holm']}", flush=True)
    for name in ("E6_strat_vs_sa_all", "E6_strat_vs_eng_all"):
        t = tests[name].get("terms") or {}
        print(f"{name} terms | strategist: {', '.join(t.get('positive', [])[:12])} | "
              f"other: {', '.join(t.get('negative', [])[:12])}", flush=True)
    share = out["counts"]["senior_share"]
    gap = round(abs(share["swe"] - share["fde"]), 3)
    out["senior_check"] = {"gap": gap, "threshold": SENIOR_GAP, "run": gap > SENIOR_GAP}
    if gap > SENIOR_GAP:
        senior = c[c.title.fillna("").str.contains(SENIOR)]
        print(f"Senior gap {gap} > {SENIOR_GAP}: E1 on senior titles only "
              f"({(senior.xgroup == 'fde').sum()} FDE, {(senior.xgroup == 'swe').sum()} SWE)", flush=True)
        sr = binary_tests(senior, p, args.quick, SENIOR_TESTS)
        for r in sr.values():
            r.pop("_boot", None)
        out["senior_check"]["tests"] = sr
    for r in tests.values():
        r.pop("_boot", None)
    out["tests"], out["E1_reading"] = tests, read_e1(tests)
    out["E4"] = {"fde": placement(c, p, "fde", args.quick), "sa_control": placement(c, p, "sa", args.quick)}
    out["E4"]["fde"]["reading"] = read_e4(out["E4"]["fde"]["table"])
    for k in ("fde", "sa_control"):
        e = out["E4"][k]
        print(f"E4 {k}: n={e['n']} companies={e['companies']} dropped={e['dropped_classes']}", flush=True)
        for cls, v in e["table"].items():
            print(f"   {cls:11} mean P={v['mean_prob']:.3f} {v['mean_prob_ci95']}  "
                  f"top={v['top_share']:.3f} {v['top_share_ci95']}", flush=True)
    a, b = tests["E5_fde_vs_sa_all"].get("accuracy"), tests["E5_fde_vs_sa_all_no_strat"].get("accuracy")
    out["E5_shift_all_companies"] = None if a is None or b is None else round(b - a, 3)
    print(f"E1 reading: {out['E1_reading']} | E4 reading: {out['E4']['fde']['reading']} | "
          f"E5 shift without strategists: {out['E5_shift_all_companies']}", flush=True)
    out["seconds"] = round(time.time() - t0)
    name = "explore_swe_confirm" if args.confirm else "explore_swe_all" if args.all else "explore_swe"
    path = P.results_dir() / (f"{name}_quick.json" if args.quick else f"{name}.json")
    path.write_text(json.dumps(out, indent=2))
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
