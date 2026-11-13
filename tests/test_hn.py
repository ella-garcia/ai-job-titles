import pandas as pd

from pipeline.hn import explode_hf_threads


def test_explode_hf_threads():
    threads = pd.DataFrame([
        {"month": "October 2026", "type": "permanent", "parent_id": 10,
         "comments": [{"id": 1, "by": "someone", "text": "Acme | FDE | Remote"}, {"id": 2, "by": "x", "text": ""}]},
        {"month": "April 2011", "type": "permanent", "parent_id": 11,
         "comments": [{"id": 3, "by": "y", "text": "Groupon is hiring"}]},
        {"month": "October 2026", "type": "freelancer", "parent_id": 12,
         "comments": [{"id": 4, "by": "z", "text": "Freelancer post"}]},
    ])
    out = explode_hf_threads(threads)
    assert list(out.columns) == ["id", "thread_id", "thread_date", "text"]   # same shape as BigQuery; no usernames
    assert out.id.tolist() == [1, 3]  # empty text and freelancer threads dropped
    assert out.thread_date.dt.strftime("%Y-%m").tolist() == ["2026-10", "2011-04"]
