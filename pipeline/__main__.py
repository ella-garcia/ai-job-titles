"""Command line: `python -m pipeline <step>` (or `make <step>`).

Steps: boards, employers, wayback, hn, kaggle, summary, env.
"""
import argparse
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
    print(f"Results in {run_dir()}")


if __name__ == "__main__":
    main()
