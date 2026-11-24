import numpy as np

from q4_ai_washing import intensity as I


def test_analysis_text_prefers_resp_and_qual():
    body = """
About us
We love AI.

Responsibilities
Deploy LLM agents with customers.

Qualifications
Python and evaluation harnesses.

Benefits
Equity.
"""
    text = I.analysis_text(body)
    assert "Deploy LLM" in text
    assert "evaluation" in text
    assert "Equity" not in text


def test_choose_threshold_prefers_precision_with_recall_floor():
    # scores: positives higher than negatives
    scores = [0.9, 0.8, 0.7, 0.4, 0.3, 0.2]
    labels = [1, 1, 1, 0, 0, 0]
    chosen = I.choose_threshold(scores, labels)
    assert chosen["threshold"] is not None
    assert chosen["precision"] == 1.0
    assert chosen["recall"] >= 0.5


def test_intensity_score_uses_embeddings(monkeypatch):
    phrases = ["deploy llm agents", "fine tune models"]
    monkeypatch.setattr(I, "seed_phrases", lambda: phrases)

    def fake_embed(texts):
        # Map known strings to fixed unit vectors.
        table = {
            "deploy llm agents": np.array([1.0, 0.0]),
            "fine tune models": np.array([0.0, 1.0]),
            "we deploy llm agents for customers": np.array([0.9, 0.1]),
        }
        out = []
        for t in texts:
            key = t if t in table else "deploy llm agents"
            v = table[key]
            out.append(v / np.linalg.norm(v))
        return np.asarray(out)

    monkeypatch.setattr(I, "_embed", fake_embed)
    score = I.intensity_score("we deploy llm agents for customers", seed_vectors=fake_embed(phrases))
    assert score > 0.8


def test_is_ai_intense_respects_threshold(monkeypatch):
    monkeypatch.setattr(I, "_cfg", lambda: {"threshold": 0.5})
    assert I.is_ai_intense(0.6) is True
    assert I.is_ai_intense(0.4) is False
    monkeypatch.setattr(I, "_cfg", lambda: {"threshold": None})
    assert I.is_ai_intense(0.9) is None
