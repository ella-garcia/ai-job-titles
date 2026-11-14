"""Q1 on the held-out set: postings first seen in snapshots after the freeze, scored once.

Refuses to run if:
  - the protocol isn't frozen (`make q1-freeze`),
  - protocol.yaml changed since freezing,
  - a held-out result already exists (pass --rerun to recompute, e.g. after more weekly pulls; the
    previous result is kept with a timestamp so nothing is silently overwritten).
Held-out postings exclude every development posting and any posting nearly identical to one.

Run: make q1-final
"""
import argparse
import datetime
import json

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from . import protocol as P
from .data import current_postings, prepare, snapshot_dates
from .evaluate import run_suite
from .run import summary_table


def held_out_corpus(p: dict, frozen: dict):
    dates = [d for d in snapshot_dates() if d > frozen["frozen_at"]]
    if not dates:
        raise SystemExit(f"No snapshots after the freeze ({frozen['frozen_at']}) yet: wait for the weekly pulls.")
    held = prepare(current_postings(dates), p)
    held = held[~held.key.isin(P.dev_keys())]
    dev = prepare(current_postings(frozen["dev_snapshots"]), p)
    if len(held) and len(dev):
        # drop held-out postings nearly identical to a development posting (e.g. a reposted job)
        vec = TfidfVectorizer(sublinear_tf=True).fit(dev.masked.tolist() + held.masked.tolist())
        sim = normalize(vec.transform(held.masked)) @ normalize(vec.transform(dev.masked)).T
        max_sim = np.asarray(sim.max(axis=1).todense()).ravel()
        held = held[max_sim < p["near_duplicate_cosine"]]
    return held.reset_index(drop=True), dates


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m q1_rebrand.final")
    parser.add_argument("--rerun", action="store_true", help="recompute with more held-out snapshots")
    args = parser.parse_args(argv)
    frozen = P.frozen()
    if not frozen:
        raise SystemExit("Not frozen: run `make q1-freeze` first.")
    if P.protocol_hash() != frozen["protocol_hash"]:
        raise SystemExit("protocol.yaml changed since freezing: the held-out run would not test the frozen "
                         "protocol. Revert the change, or re-freeze if no held-out run has happened yet.")
    out = P.results_dir() / "final_results.json"
    if out.exists() and not args.rerun:
        raise SystemExit(f"A held-out result already exists ({out}). Pass --rerun to recompute; "
                         "the previous file is kept with a timestamp.")
    if out.exists():
        out.rename(out.with_name(f"final_results_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"))
    p = P.load()
    corpus, dates = held_out_corpus(p, frozen)
    print(f"Held-out set: {len(corpus):,} new postings from snapshots {dates}")
    results = run_suite(corpus, p)
    results.update({"status": "held-out", "protocol": p["version"], "protocol_hash": frozen["protocol_hash"],
                    "frozen_commit": frozen["git_commit"], "git_commit": P.git("rev-parse", "HEAD"),
                    "held_out_snapshots": dates})
    out.write_text(json.dumps(results, indent=2))
    print(summary_table(results))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
