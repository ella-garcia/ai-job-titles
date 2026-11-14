"""Archived postings: job keys, titles from URLs and pages, and append-safe files."""
import gzip
import json

import pytest

from pipeline.jsonl import append, read_lenient
from pipeline.wayback_postings import extract_title, job_key, title_from_url


@pytest.mark.parametrize("a, b", [
    ("http://www.palantir.com:80/careers/OpenPosDetail?id=a0m800&utm=x", "https://palantir.com/careers/OpenPosDetail?id=a0m800"),
    ("https://jobs.lever.co/palantir/abc-123?lever-origin=applied", "https://jobs.lever.co/palantir/abc-123/"),
])
def test_job_key_ignores_scheme_port_and_tracking(a, b):
    assert job_key(a) == job_key(b)


def test_job_key_keeps_job_id():
    assert job_key("https://x.com/careers/Detail?id=1") != job_key("https://x.com/careers/Detail?id=2")


@pytest.mark.parametrize("url, expected", [
    ("https://www.databricks.com/company/careers/-field-engineering/-partner-solutions-architect-83478800",
     "partner solutions architect"),
    ("https://jobs.lever.co/palantir/0a43451d-df80-42ac-ae99-cce2af9b0f37", None),     # UUID only
    ("http://www.palantir.com/careers/OpenPosDetail?id=a0m80000005LUmSAAW", None),       # one word
])
def test_title_from_url(url, expected):
    assert title_from_url(url) == expected


def test_extract_title_skips_company_heading():
    html = "<title>Open Positions | Palantir</title><h1>Palantir</h1><h1>Forward Deployed Software Engineer</h1>"
    assert extract_title(html, "palantir") == "Forward Deployed Software Engineer"


@pytest.mark.parametrize("og, expected", [
    ("Palantir Technologies - Deployment Strategist", "Deployment Strategist"),
    ("Solutions Architect (West) | Databricks", "Solutions Architect (West)"),
])
def test_extract_title_strips_company_name(og, expected):
    company = "palantir" if "Palantir" in og else "databricks"
    assert extract_title(f'<meta property="og:title" content="{og}">', company) == expected


def test_read_lenient_survives_interrupted_writes(tmp_path):
    plain = tmp_path / "x.jsonl"
    append(plain, {"a": 1})
    append(plain, {"a": 2})
    with open(plain, "a") as fh:
        fh.write('{"a": 3, "trunc')                  # interrupted mid-line
    assert [r["a"] for r in read_lenient(plain)] == [1, 2]

    gz = tmp_path / "x.jsonl.gz"
    with gzip.open(gz, "wt") as fh:
        for i in range(200):
            fh.write(json.dumps({"a": i, "pad": "x" * 200}) + "\n")
    data = gz.read_bytes()
    gz.write_bytes(data[: len(data) // 2])            # truncated gzip block
    records = read_lenient(gz)
    assert records and records[0]["a"] == 0 and len(records) < 200
