"""Score AI-intensity on a local golden or corpus CSV (body text stays under AJT_DATA)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from pipeline.config import data_dir, run_dir, seed_everything

from .intensity import choose_threshold, intensity_score, is_ai_intense, seed_phrases


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m q4_ai_washing")
    parser.add_argument(
        "--input",
        type=Path,
        help="CSV with a text column (and optional ai_bullet labels). Default: processed/golden/with_text.csv",
    )
    parser.add_argument("--text-col", default="text", help="column with posting body text")
    parser.add_argument("--label-col", default="ai_bullet", help="optional golden labels 0/1")
    args = parser.parse_args(argv)

    seed_everything()
    path = args.input or (data_dir() / "processed" / "golden" / "with_text.csv")
    if not path.exists():
        print(
            f"No input at {path}. Build a local CSV with posting bodies under AJT_DATA "
            "(never commit it), or pass --input."
        )
        print(f"Seed phrases loaded: {len(seed_phrases())}")
        return

    df = pd.read_csv(path)
    if args.text_col not in df.columns:
        raise SystemExit(f"{path} needs a {args.text_col!r} column")

    scores = [intensity_score(t) for t in df[args.text_col].fillna("")]
    df = df.assign(ai_intensity=scores)
    thr_applied = [is_ai_intense(s) for s in scores]
    df["ai_intense"] = thr_applied

    out = run_dir()
    # Write scores only for rows that already have an ID; drop raw text from the run artifact.
    keep = [c for c in df.columns if c != args.text_col]
    df[keep].to_csv(out / "q4_ai_intensity_scores.csv", index=False)

    summary: dict = {
        "n": int(len(df)),
        "mean_score": round(float(sum(scores) / len(scores)), 4) if scores else None,
        "seeds": len(seed_phrases()),
        "threshold_configured": is_ai_intense(0.0) is not None,
    }
    if args.label_col in df.columns:
        labels = pd.to_numeric(df[args.label_col], errors="coerce")
        mask = labels.notna()
        if mask.any():
            chosen = choose_threshold(df.loc[mask, "ai_intensity"].tolist(),
                                      labels[mask].astype(int).tolist())
            summary["chosen_threshold"] = chosen
            (out / "q4_threshold.json").write_text(json.dumps(chosen, indent=2))
    (out / "q4_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"Results in {out}")


if __name__ == "__main__":
    main()
