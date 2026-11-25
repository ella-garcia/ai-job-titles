"""Cohen's kappa between two author label CSVs (family, ai_bullet, section)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from pipeline.config import run_dir

FIELDS = ("family_human", "ai_bullet", "section")


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    if "posting_id" not in df.columns:
        raise ValueError(f"{path} needs a posting_id column")
    return df


def agreement(path_a: Path, path_b: Path, fields: tuple[str, ...] = FIELDS) -> dict:
    a = _load(path_a).set_index("posting_id")
    b = _load(path_b).set_index("posting_id")
    shared = a.index.intersection(b.index)
    out: dict = {"n_shared": int(len(shared)), "fields": {}}
    for field in fields:
        if field not in a.columns or field not in b.columns:
            continue
        ya = a.loc[shared, field].astype(str).str.strip()
        yb = b.loc[shared, field].astype(str).str.strip()
        mask = (ya != "") & (yb != "")
        if mask.sum() == 0:
            out["fields"][field] = {"n": 0, "kappa": None}
            continue
        kappa = float(cohen_kappa_score(ya[mask], yb[mask]))
        out["fields"][field] = {
            "n": int(mask.sum()),
            "kappa": round(kappa, 4),
            "raw_agreement": round(float((ya[mask] == yb[mask]).mean()), 4),
        }
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m validation.kappa")
    parser.add_argument("--a", required=True, type=Path, help="labels CSV for author A")
    parser.add_argument("--b", required=True, type=Path, help="labels CSV for author B")
    args = parser.parse_args(argv)
    result = agreement(args.a, args.b)
    out = run_dir() / "golden_kappa.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
