"""Exploratory Q1 tests by title type, outside the frozen protocol (development set only).

1. FDE vs each SA title type on its own: Solutions Architect titles vs Solutions / Customer / Sales Engineer
   titles. The frozen headline pools them; this checks that FDE is equally far from both.
2. FDE vs post-sales technical support (Support Engineer, Customer Success Engineer, Technical Support): a
   second rival reading, like the technical-consultant test.

Same sampling, model, cross-validation, bootstrap and chance level as the frozen protocol. The labels here
are defined in this file only (not in config.yaml), so the frozen protocol hash is unchanged. The support
group's title words are masked as well, on top of the frozen masking.

Results are exploratory and never replace the frozen tests.

Run: uv run python -m q1_rebrand.explore_titles   [--quick: no bootstrap/permutations, one seed]
"""
import argparse
import json
import re
import time

import numpy as np

from . import protocol as P
from .evaluate import compare, run_test
from .run import development_corpus

SUPPORT_TITLE = re.compile(r"support engineer|customer success engineer|technical support", re.I)
INTERNAL_IT = re.compile(r"\bit support|\bdesktop support|help ?desk", re.I)   # internal IT, not customer-facing
SUPPORT_WORDS = re.compile(r"(technical |customer |product )?support engineer\w*|customer success engineer\w*|"
                           r"technical support( specialist| engineer)?\w*", re.I)
EXCLUDED = {"fde", "sa_ce", "tech_consultant", "fd_hybrid", "fd_nontech", "pm", "ai_pm"}

TESTS = {
    # reference: the frozen headline, re-run here so every number below comes from the same code and seed
    "headline":          {"label": "family", "positive": "fde", "negative": "sa_ce", "within_company": True},
    "fde_vs_sa_architect": {"label": "xgroup", "positive": "fde", "negative": "sa_architect", "within_company": True},
    "fde_vs_sa_engineer":  {"label": "xgroup", "positive": "fde", "negative": "sa_engineer", "within_company": True},
    "fde_vs_sa_architect_all": {"label": "xgroup", "positive": "fde", "negative": "sa_architect",
                                "within_company": False},
    "fde_vs_sa_engineer_all":  {"label": "xgroup", "positive": "fde", "negative": "sa_engineer",
                                "within_company": False},
    "near_synonym":      {"label": "xgroup", "positive": "sa_architect", "negative": "sa_engineer",
                          "within_company": True},
    "fde_vs_support":    {"label": "xgroup", "positive": "fde", "negative": "support", "within_company": True},
    "fde_vs_support_all": {"label": "xgroup", "positive": "fde", "negative": "support", "within_company": False},
    "support_vs_sa":     {"label": "xgroup", "positive": "support", "negative": ["sa_architect", "sa_engineer"],
                          "within_company": True},
}

COMPARISONS = [
    ["fde_vs_sa_architect", "fde_vs_sa_engineer", "greater"],  # two-sided reading: report both p's
    ["fde_vs_sa_engineer", "fde_vs_sa_architect", "greater"],
    ["fde_vs_support", "near_synonym", "greater"],             # FDE is not a renamed support engineer
    ["fde_vs_support", "headline", "less"],                    # ... closer to support than to SA?
]


def label(corpus):
    """xgroup: fde, sa_architect, sa_engineer, support or other."""
    g = np.select(
        [corpus.family == "fde",
         (corpus.family == "sa_ce") & (corpus["sub"] == "architect"),
         (corpus.family == "sa_ce") & (corpus["sub"] == "engineer"),
         ~corpus.family.isin(EXCLUDED) & corpus.title.fillna("").str.contains(SUPPORT_TITLE)
         & ~corpus.title.fillna("").str.contains(INTERNAL_IT)],
        ["fde", "sa_architect", "sa_engineer", "support"], default="other")
    out = corpus.assign(xgroup=g)
    out["masked"] = out.masked.str.replace(SUPPORT_WORDS, " ", regex=True)
    return out


def _spec(spec, corpus):
    """Pool a list of negatives into one label so the frozen sampling code can be reused unchanged."""
    if isinstance(spec["negative"], list):
        corpus = corpus.assign(xgroup=corpus.xgroup.where(~corpus.xgroup.isin(spec["negative"]), "pooled"))
        spec = {**spec, "negative": "pooled"}
    return spec, corpus


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="accuracy only, no bootstrap or permutations")
    args = ap.parse_args(argv)
    p = P.load()
    t0 = time.time()
    corpus, dates = development_corpus(p)
    corpus = label(corpus)
    print(f"Development set: {len(corpus):,} postings; groups:",
          corpus.xgroup.value_counts().drop("other", errors="ignore").to_dict())
    results = {}
    for name, spec in TESTS.items():
        s, c = _spec(spec, corpus)
        results[name] = run_test(c, s, p, p["seed"], full=not args.quick)
        r = results[name]
        if "error" in r:
            print(f"{name:26} {r['error']}")
        else:
            print(f"{name:26} n={r['n']:4} companies={len(r['companies']):2} acc={r['accuracy']:.3f} "
                  f"CI={r.get('ci95')} chance95={r.get('chance_95th')}  {r['companies']}")
    out = {"status": "exploratory (development set, outside the frozen protocol)", "protocol": p["version"],
           "git_commit": P.git("rev-parse", "HEAD"), "snapshots": dates, "seconds": round(time.time() - t0)}
    if not args.quick:
        comps = compare(results, COMPARISONS)
        for cmp in comps:
            if "p" in cmp:
                print(f"{cmp['a']} {'>' if cmp['direction'] == 'greater' else '<'} {cmp['b']}: "
                      f"diff {cmp['difference']:+.3f} {cmp['ci95']}, p={cmp['p']}, Holm p={cmp['p_holm']}")
        out["comparisons"] = comps
    for r in results.values():
        r.pop("_boot", None)
    out["tests"] = results
    path = P.results_dir() / ("explore_titles_quick.json" if args.quick else "explore_titles.json")
    path.write_text(json.dumps(out, indent=2))
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
