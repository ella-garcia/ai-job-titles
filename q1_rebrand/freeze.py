"""Freeze the Q1 protocol: after this, settings can't change without invalidating the held-out run.

Writes q1_rebrand/frozen/frozen_config.json (protocol hash, git commit, freeze date, development
snapshot dates) and dev_keys.txt (hashes of every development posting, so held-out postings can be
checked as new). Both are committed; they hold no posting text.

Run: make q1-freeze   (refuses if the Q1 code or protocol has uncommitted changes, or if already frozen)
"""
import argparse
import datetime
import json

from . import protocol as P
from .data import current_postings, prepare, snapshot_dates


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m q1_rebrand.freeze")
    parser.add_argument("--force", action="store_true", help="re-freeze (only before any held-out run)")
    args = parser.parse_args(argv)
    if P.frozen() and not args.force:
        raise SystemExit(f"Already frozen on {P.frozen()['frozen_at']}. Re-freezing changes the held-out set; "
                         "use --force only if `make q1-final` has never been run.")
    if P.git("status", "--porcelain", "--", "q1_rebrand", "pipeline", "config.yaml"):
        raise SystemExit("Commit the Q1 code, pipeline and config.yaml first: the frozen config records the commit.")
    p = P.load()
    dates = snapshot_dates()
    if not dates:
        raise SystemExit("No snapshots found: run `make snapshots` first.")
    corpus = prepare(current_postings(dates), p)
    P.FROZEN_DIR.mkdir(exist_ok=True)
    P.DEV_KEYS.write_text("\n".join(sorted(corpus.key)) + "\n")
    config = {"protocol": p["version"], "protocol_hash": P.protocol_hash(), "git_commit": P.git("rev-parse", "HEAD"),
              "frozen_at": max(dates), "frozen_on": datetime.date.today().isoformat(),
              "dev_snapshots": dates, "dev_postings": int(len(corpus))}
    P.FROZEN.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps(config, indent=2))
    print(f"\nFrozen. Commit {P.FROZEN_DIR.relative_to(P.ROOT)}/ so your co-author uses the same freeze.")


if __name__ == "__main__":
    main()
