"""Cluster unmatched titles (JobBERT + HDBSCAN) and suggest family_overrides rows.

Requires the analysis extra: `uv sync --extra analysis`. Writes aggregate cluster reports under
runs/<date>/ — never raw posting bodies. Hand decisions go into pipeline/family_overrides.csv.
"""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd

from .config import CFG, SEED, run_dir
from .families import FAMILY_PATTERNS, family
from .title_coverage import load_titles


def _cfg() -> dict:
    return CFG.get("title_clustering", {})


def unmatched_titles(titles: pd.DataFrame | None = None) -> pd.DataFrame:
    """Distinct normalised titles currently labelled other (candidates for clustering)."""
    df = titles if titles is not None else load_titles()
    if df.empty:
        return df
    other = df[df.family == "other"].copy()
    # Re-check: only titles with no seed regex hit (overrides may already label some).
    mask = ~other.title_norm.map(lambda t: any(p.search(t) for p in FAMILY_PATTERNS.values()))
    other = other[mask]
    counts = (
        other.groupby("title_norm", dropna=False)
        .agg(postings=("title", "size"), example_title=("title", "first"), companies=("company", "nunique"))
        .reset_index()
        .sort_values("postings", ascending=False)
    )
    return counts


def merge_near_duplicates(titles: list[str], ratio: int | None = None) -> dict[str, str]:
    """Map each title_norm to a canonical spelling via rapidfuzz (ratio ≥ threshold)."""
    try:
        from rapidfuzz import fuzz
    except ImportError as exc:  # pragma: no cover - exercised when analysis extra missing
        raise ImportError("rapidfuzz is required: uv sync --extra analysis") from exc

    threshold = ratio if ratio is not None else int(_cfg().get("rapidfuzz_ratio", 92))
    canon: dict[str, str] = {}
    representatives: list[str] = []
    for title in sorted(titles, key=len):
        matched = None
        for rep in representatives:
            if fuzz.ratio(title, rep) >= threshold:
                matched = rep
                break
        if matched is None:
            representatives.append(title)
            canon[title] = title
        else:
            canon[title] = matched
    return canon


def embed_titles(titles: list[str], model_name: str | None = None):
    """JobBERT embeddings for titles (max sequence length 64)."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise ImportError("sentence-transformers is required: uv sync --extra analysis") from exc

    name = model_name or _cfg().get("model", "TechWolf/JobBERT-v2")
    model = SentenceTransformer(name)
    return model.encode(titles, show_progress_bar=False, normalize_embeddings=True)


def cluster_embeddings(embeddings, min_cluster_size: int | None = None) -> list[int]:
    try:
        import hdbscan
    except ImportError as exc:  # pragma: no cover
        raise ImportError("hdbscan is required: uv sync --extra analysis") from exc

    size = min_cluster_size if min_cluster_size is not None else int(_cfg().get("min_cluster_size", 10))
    clusterer = hdbscan.HDBSCAN(min_cluster_size=size, metric="euclidean", cluster_selection_method="eom")
    return list(clusterer.fit_predict(embeddings))


def run(dates: list[str] | None = None) -> dict:
    """Cluster unmatched titles and write suggestion tables for hand labelling."""
    titles = load_titles(dates)
    candidates = unmatched_titles(titles)
    out = run_dir()
    if candidates.empty:
        summary = {"candidates": 0, "clusters": 0}
        (out / "title_clusters_summary.json").write_text(json.dumps(summary, indent=2))
        return summary

    canon = merge_near_duplicates(candidates.title_norm.tolist())
    candidates = candidates.assign(canon=candidates.title_norm.map(canon))
    merged = (
        candidates.groupby("canon", as_index=False)
        .agg(
            postings=("postings", "sum"),
            variants=("title_norm", "count"),
            example_title=("example_title", "first"),
            companies=("companies", "sum"),
        )
        .sort_values("postings", ascending=False)
    )
    merged.to_csv(out / "title_clusters_merged_titles.csv", index=False)

    vectors = embed_titles(merged.canon.tolist())
    labels = cluster_embeddings(vectors)
    merged = merged.assign(cluster_id=labels)
    merged.to_csv(out / "title_clusters.csv", index=False)

    # Per-cluster examples for hand assignment (aggregates / titles only).
    rows = []
    by_cluster: dict[int, list[str]] = defaultdict(list)
    for row in merged.itertuples(index=False):
        by_cluster[int(row.cluster_id)].append(row.canon)
    for cluster_id, members in sorted(by_cluster.items(), key=lambda x: (-len(x[1]), x[0])):
        if cluster_id < 0:
            continue
        rows.append({
            "cluster_id": cluster_id,
            "size": len(members),
            "examples": " | ".join(members[:12]),
            "suggested_family": "",  # fill by hand, then copy into family_overrides.csv
        })
    pd.DataFrame(rows).to_csv(out / "title_clusters_for_labelling.csv", index=False)

    # Template override rows (blank family) for the largest clusters' members.
    override_rows = []
    labelled = merged[merged.cluster_id >= 0]
    for row in labelled.itertuples(index=False):
        override_rows.append({
            "title_norm": row.canon,
            "family": "",
            "cluster_id": int(row.cluster_id),
            "note": "fill family then append to pipeline/family_overrides.csv",
            "decided_by": "",
            "date": "",
        })
    pd.DataFrame(override_rows).to_csv(out / "title_cluster_override_template.csv", index=False)

    summary = {
        "seed": SEED,
        "candidates": int(len(candidates)),
        "merged_titles": int(len(merged)),
        "clusters": int(sum(1 for c in set(labels) if c >= 0)),
        "noise": int(sum(1 for c in labels if c < 0)),
        "model": _cfg().get("model", "TechWolf/JobBERT-v2"),
        "min_cluster_size": int(_cfg().get("min_cluster_size", 10)),
        "rapidfuzz_ratio": int(_cfg().get("rapidfuzz_ratio", 92)),
        # Sanity: clustering must not change current family() without overrides.
        "sample_still_other": int(sum(family(t) == "other" for t in merged.canon.head(20))),
    }
    (out / "title_clusters_summary.json").write_text(json.dumps(summary, indent=2))
    return summary
