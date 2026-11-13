"""Hacker News "Who is Hiring" comments, from BigQuery (preferred) or the Hugging Face copy.

BigQuery needs GCP_PROJECT and credentials: locally `gcloud auth application-default login`;
in Colab, the notebook signs you in.
"""
import pandas as pd

from .config import TODAY, data_dir, run_dir, secret
from .manifest import log_download

SQL = """
WITH threads AS (
  SELECT id, timestamp
  FROM `bigquery-public-data.hacker_news.full`
  WHERE type = 'story' AND `by` = 'whoishiring'
    AND LOWER(title) LIKE 'ask hn: who is hiring%'
)
SELECT c.id, c.parent AS thread_id, t.timestamp AS thread_date, c.text
FROM `bigquery-public-data.hacker_news.full` c
JOIN threads t ON c.parent = t.id
WHERE c.type = 'comment' AND c.text IS NOT NULL
  AND (c.deleted IS NULL OR c.deleted = FALSE)
"""
HF_DATASET = "brusic/hacker-news-who-is-hiring-posts"


def fetch_hn(date: str = TODAY) -> pd.DataFrame:
    out = data_dir() / "raw" / "hn" / date
    out.mkdir(parents=True, exist_ok=True)
    path = out / "comments.parquet"
    if path.exists():
        return pd.read_parquet(path)
    project = secret("GCP_PROJECT")
    if project:
        from google.cloud import bigquery

        client = bigquery.Client(project=project)
        dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        print(f"BigQuery will scan {dry.total_bytes_processed / 1e9:.1f} GB (free tier: 1,000 GB/month)")
        df = client.query(SQL).to_dataframe()
        df.to_parquet(path)
        log_download("hn_bigquery", "bigquery-public-data.hacker_news.full", path, rows=len(df),
                     licence="HN public data")
    else:
        print("No GCP_PROJECT set: using the Hugging Face dataset instead.")
        from datasets import load_dataset

        ds = load_dataset(HF_DATASET)
        df = explode_hf_threads(ds[list(ds)[0]].to_pandas())
        df.to_parquet(path)
        log_download("hn_huggingface", f"hf://datasets/{HF_DATASET}", path, rows=len(df), licence="see dataset card")
    return df


def explode_hf_threads(threads: pd.DataFrame) -> pd.DataFrame:
    """Hugging Face rows are one thread each (month, type, parent_id, comments[]).
    Return one row per comment in the same columns as the BigQuery query: id, thread_id, thread_date, text.
    Keeps only "Who is hiring" threads (type 'permanent'); drops usernames."""
    rows = []
    for _, t in threads[threads["type"] == "permanent"].iterrows():
        thread_date = pd.to_datetime("1 " + t["month"], format="%d %B %Y")
        for c in t["comments"]:
            if c.get("text"):
                rows.append({"id": c["id"], "thread_id": t["parent_id"], "thread_date": thread_date, "text": c["text"]})
    return pd.DataFrame(rows, columns=["id", "thread_id", "thread_date", "text"])


def monthly_check(df: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Comments per month and the months missing since April 2011."""
    date_col = "thread_date" if "thread_date" in df.columns else next(
        c for c in df.columns if "date" in c.lower() or "time" in c.lower())
    months = pd.to_datetime(df[date_col], utc=True).dt.tz_localize(None).dt.to_period("M").value_counts().sort_index()
    expected = pd.period_range("2011-04", pd.Timestamp.today(), freq="M")
    missing = [str(m) for m in expected.difference(months.index)]
    months.to_csv(run_dir() / "hn_comments_per_month.csv")
    return months, missing
