"""AI-intensity: max cosine similarity of posting sections to AI seed phrases."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from pipeline.config import CFG
from pipeline.sectioner import section_text

HERE = Path(__file__).resolve().parent
SEEDS_PATH = HERE / "seeds.yaml"


@lru_cache(maxsize=1)
def seed_phrases() -> list[str]:
    data = yaml.safe_load(SEEDS_PATH.read_text(encoding="utf-8"))
    phrases = list(data.get("phrases") or [])
    if not phrases:
        raise ValueError(f"No phrases in {SEEDS_PATH}")
    return phrases


def _cfg() -> dict:
    return CFG.get("ai_intensity", {})


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise ImportError("sentence-transformers is required: uv sync --extra analysis") from exc
    name = _cfg().get("model", "sentence-transformers/all-MiniLM-L6-v2")
    return SentenceTransformer(name)


def _embed(texts: list[str]):
    return _model().encode(texts, show_progress_bar=False, normalize_embeddings=True)


def analysis_text(body: str | None, prefer_sections: bool = True) -> str:
    """Text used for scoring: responsibilities + qualifications when sectioned."""
    if not prefer_sections:
        return (body or "").strip()
    parts = section_text(body)
    joined = "\n".join(p for p in (parts["text_resp"], parts["text_qual"]) if p).strip()
    return joined or (body or "").strip()


def intensity_score(body: str | None, seed_vectors=None) -> float:
    """Max cosine similarity between the posting analysis text and any seed phrase."""
    text = analysis_text(body)
    if not text:
        return 0.0
    seeds = seed_vectors if seed_vectors is not None else _embed(seed_phrases())
    doc = _embed([text])[0]
    sims = seeds @ doc
    return float(np.max(sims))


def is_ai_intense(score: float, threshold: float | None = None) -> bool | None:
    """Apply the configured threshold; None if the threshold is not set yet."""
    thr = _cfg().get("threshold") if threshold is None else threshold
    if thr is None:
        return None
    return bool(score >= float(thr))


def choose_threshold(scores: list[float], labels: list[int]) -> dict:
    """Pick the threshold that maximises precision among thresholds with recall ≥ min_recall."""
    y = np.asarray(labels, dtype=int)
    s = np.asarray(scores, dtype=float)
    min_recall = float(_cfg().get("min_recall", 0.5))
    candidates = sorted(set(s.tolist()))
    best = {"threshold": None, "precision": None, "recall": None, "f1": None}
    for thr in candidates:
        pred = (s >= thr).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        if rec < min_recall:
            continue
        if best["precision"] is None or prec > best["precision"]:
            best = {"threshold": float(thr), "precision": round(prec, 4),
                    "recall": round(rec, 4), "f1": round(f1, 4)}
    return best
