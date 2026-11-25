import pandas as pd
import pytest

from pipeline.cluster_titles import merge_near_duplicates, unmatched_titles


def test_merge_near_duplicates():
    pytest.importorskip("rapidfuzz")
    canon = merge_near_duplicates(
        ["solutions architect", "solution architect", "product manager"],
        ratio=92,
    )
    assert canon["solutions architect"] == canon["solution architect"]
    assert canon["product manager"] == "product manager"


def test_unmatched_titles_filters_other():
    df = pd.DataFrame({
        "family": ["other", "other", "fde"],
        "title": ["Office Manager", "Office Manager", "Forward Deployed Engineer"],
        "title_norm": ["office manager", "office manager", "forward deployed engineer"],
        "company": ["a", "b", "c"],
    })
    out = unmatched_titles(df)
    assert list(out.title_norm) == ["office manager"]
    assert int(out.iloc[0].postings) == 2
