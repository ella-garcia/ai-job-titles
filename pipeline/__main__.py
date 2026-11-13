"""Command line: `python -m pipeline <step>` (or `make <step>`).

Steps: boards, employers, wayback, hn, kaggle, summary, env, sync-snapshots.
"""
import argparse
import shutil
import subprocess
import sys

import pandas as pd

from .config import ROOT, data_dir, run_dir, seed_everything


def record_environment() -> None:
    """Save the exact package versions and git commit next to today's results."""
    out = run_dir()
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    if not freeze.strip():  # uv environments may not ship pip
        freeze = subprocess.run(["uv", "pip", "freeze"], capture_output=True, text=True, cwd=ROOT).stdout
    (out / "pip-freeze.txt").write_text(freeze)
    commit = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"],
                            capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    note = (commit or "no commit yet") + (" (uncommitted changes)" if dirty else "")
    (out / "git-commit.txt").write_text(note + "\n")


def sync_snapshots() -> None:
    """Copy weekly snapshots from the local data-branch checkout (.snapshots/) into AJT_DATA/raw.

    Only new files are copied; nothing in AJT_DATA is overwritten or deleted.
    """
    if not (ROOT / ".snapshots").exists():
        print("No .snapshots/ checkout yet: run `make snapshots`.")
        return
    src = ROOT / ".snapshots" / "snapshots" / "raw"
    if not src.exists():
        print("The data branch has no snapshots yet: the weekly-pull workflow hasn't run.")
        return
    dst = data_dir() / "raw"
    copied = 0
    for path in sorted(src.rglob("*")):
        target = dst / path.relative_to(src)
        if path.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1
    print(f"Copied {copied} new snapshot files into {dst}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("boards", help="full Greenhouse / Lever / Ashby boards")
    emp = sub.add_parser("employers", help="big employers by keyword search")
    emp.add_argument("--only", nargs="*", help="employer names from config.yaml")
    emp.add_argument("--terms", nargs="*", help="override search terms (for testing)")
    sub.add_parser("wayback", help="Wayback coverage test")
    sub.add_parser("hn", help="HN Who is Hiring")
    sub.add_parser("kaggle", help="Kaggle LinkedIn sets")
    sub.add_parser("summary", help="coverage tables and week-1 summary")
    sub.add_parser("env", help="record package versions and git commit")
    sub.add_parser("sync-snapshots", help="copy weekly snapshots from .snapshots/ into AJT_DATA")
    args = parser.parse_args(argv)

    seed_everything()
    pd.set_option("display.width", 200)
    print(f"Data folder: {data_dir()}")
    record_environment()

    if args.step == "boards":
        from .boards import fetch_boards
        fetch_boards()
    elif args.step == "employers":
        from .employers import fetch_employers
        fetch_employers(only=args.only, terms=args.terms)
    elif args.step == "wayback":
        from .wayback import coverage
        result = coverage()
        print(result["estimate"].est_usable.unstack("period", fill_value=0).to_string())
    elif args.step == "hn":
        from .hn import fetch_hn, monthly_check
        months, missing = monthly_check(fetch_hn())
        print(f"{len(months)} months present, {len(missing)} missing: {missing[:24]}")
    elif args.step == "kaggle":
        from .kaggle_data import fetch_kaggle
        fetch_kaggle()
    elif args.step == "summary":
        from .summary import coverage, week1_summary
        print(coverage().to_string())
        print(week1_summary())
    elif args.step == "sync-snapshots":
        sync_snapshots()
    print(f"Results in {run_dir()}")


if __name__ == "__main__":
    main()
