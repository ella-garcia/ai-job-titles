"""Text cleaning shared by all sources (plan step 1).

Boilerplate removal: a sentence that appears in more than `share` of one company's postings (within
one source) is company boilerplate (site navigation, "About us", benefits, equal-opportunity text) and
is dropped. Companies with fewer than `min_docs` postings are left as they are.
"""
import re
from collections import Counter

import pandas as pd

SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\s+[•·▪◦]\s+|\s{2,}")


def sentences(text: str) -> list[str]:
    parts = (s.strip().lstrip("•·▪◦-* ").strip() for s in SENTENCE_SPLIT.split(text or ""))
    return [s for s in parts if len(s) > 2]


def _norm(sentence: str) -> str:
    return re.sub(r"\d+", "0", re.sub(r"\s+", " ", sentence.lower())).strip()


def remove_boilerplate(df: pd.DataFrame, text_col: str = "text", group_cols: tuple = ("company", "source"),
                       share: float = 0.3, min_docs: int = 10) -> pd.Series:
    """Text with boilerplate sentences removed, aligned with df.index."""
    out = df[text_col].fillna("").copy()
    for _, g in df.groupby(list(group_cols)):
        if len(g) < min_docs:
            continue
        split = {i: sentences(t) for i, t in g[text_col].fillna("").items()}
        doc_freq = Counter(s for sents in split.values() for s in {_norm(x) for x in sents})
        limit = share * len(g)
        common = {s for s, n in doc_freq.items() if n > limit}
        for i, sents in split.items():
            out.at[i] = " ".join(s for s in sents if _norm(s) not in common)
    return out
