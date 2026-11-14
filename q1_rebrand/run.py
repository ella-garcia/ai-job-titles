"""Q1 on the development set: every snapshot collected so far (or, once frozen, up to the freeze date).

Results are labelled EXPLORATORY: this is the data used to make decisions. The held-out number comes
from `make q1-final`, on postings first seen after the freeze.

Run: make q1   (or uv run python -m q1_rebrand.run)
"""
import json
import time

from . import protocol as P
from .data import current_postings, prepare, snapshot_dates
from .evaluate import run_suite


def development_corpus(p: dict):
    frozen = P.frozen()
    dates = snapshot_dates()
    if frozen:
        dates = [d for d in dates if d <= frozen["frozen_at"]]
    return prepare(current_postings(dates), p), dates


def summary_table(results: dict) -> str:
    lines = [f"{'test':15} {'n':>5} {'cos':>4} {'acc':>6} {'95% CI':>14} {'chance95':>9}  C"]
    for name, r in results["tests"].items():
        if "error" in r:
            lines.append(f"{name:15} {r['error']}")
            continue
        lines.append(f"{name:15} {r['n']:5} {len(r['companies']):4} {r['accuracy']:6.3f} "
                     f"{str(r['ci95']):>14} {r['chance_95th']:9.3f}  {r['chosen_c']}")
    for c in results["comparisons"]:
        if "p" in c:
            lines.append(f"{c['a']} {'>' if c['direction'] == 'greater' else '<'} {c['b']}: "
                         f"diff {c['difference']:+.3f} {c['ci95']}, p={c['p']}, Holm p={c['p_holm']}")
    s = results["headline_over_seeds"]
    lines.append(f"headline over {len(s['accuracies'])} seeds: mean {s['mean']}, sd {s['sd']}")
    return "\n".join(lines)


def main() -> None:
    p = P.load()
    t0 = time.time()
    corpus, dates = development_corpus(p)
    print(f"Development set: {len(corpus):,} postings from snapshots {dates}")
    results = run_suite(corpus, p)
    results.update({"status": "exploratory (development set)", "protocol": p["version"],
                    "protocol_hash": P.protocol_hash(), "git_commit": P.git("rev-parse", "HEAD"),
                    "snapshots": dates, "seconds": round(time.time() - t0)})
    out = P.results_dir() / "dev_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(summary_table(results))
    h = results["tests"].get("headline", {}).get("terms")
    if h:
        print("\nStable terms towards FDE:", ", ".join(h["positive"][:15]))
        print("Stable terms towards SA: ", ", ".join(h["negative"][:15]))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
