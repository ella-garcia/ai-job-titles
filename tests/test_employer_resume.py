"""Employer search: skipping listings without links, and resuming after a rate limit."""
import gzip
import json

import pytest
import requests

from pipeline import employers

CFG = {"group": "mag7", "system": "fake"}


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("AJT_DATA", str(tmp_path))
    monkeypatch.setitem(employers.CFG, "employers", {"fakeco": CFG})
    return tmp_path


def rate_limited():
    response = requests.Response()
    response.status_code = 429
    return requests.HTTPError("429 Too Many Requests", response=response)


def make_search(fail_on: set[str], calls: list[str]):
    def search(cfg, term):
        calls.append(term)
        if term in fail_on:
            raise rate_limited()
        yield {"id": f"{term}-1", "title": "Forward Deployed Engineer" if term == "fde" else "Office Manager",
               "location": "Madrid, ES", "text": "full text"}
        yield {"id": "shared", "title": "Solutions Architect", "location": "Seattle", "text": "full text"}
    return search


def test_resume_after_rate_limit(data, monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(employers.SEARCH, "fake", make_search({"pm"}, calls))
    employers.fetch_employers(terms=["fde", "pm"], date="2026-11-13")

    out = data / "raw" / "employers" / "2026-11-13"
    assert not (out / "fakeco.jsonl.gz").exists()
    assert json.loads((out / "fakeco.progress.json").read_text()) == {"terms_done": ["fde"]}
    assert len(employers._read_jsonl(out / "fakeco.partial.jsonl.gz")) == 2
    assert employers.load_employers("2026-11-13").empty  # partial results are not loaded

    calls.clear()
    monkeypatch.setitem(employers.SEARCH, "fake", make_search(set(), calls))
    employers.fetch_employers(terms=["fde", "pm"], date="2026-11-13")

    assert calls == ["pm"]  # the finished term is not searched again
    assert not (out / "fakeco.partial.jsonl.gz").exists() and not (out / "fakeco.progress.json").exists()
    records = {r["id"]: r for r in employers._read_jsonl(out / "fakeco.jsonl.gz")}
    assert set(records) == {"fde-1", "pm-1", "shared"}
    assert records["shared"]["terms"] == ["fde", "pm"]
    assert records["fde-1"]["family"] == "fde" and records["fde-1"]["spain"] is True
    assert len(employers.load_employers("2026-11-13")) == 3


def test_detail_rate_limit_stops_instead_of_marking_failed(data, monkeypatch):
    def search(cfg, term):
        yield {"id": "a", "title": "Solutions Architect", "location": "Paris"}

    def detail(cfg, rec):
        raise rate_limited()

    monkeypatch.setitem(employers.SEARCH, "fake", search)
    monkeypatch.setitem(employers.DETAIL, "fake", detail)
    employers.fetch_employers(terms=["sa"], date="2026-11-13")
    out = data / "raw" / "employers" / "2026-11-13"
    saved = employers._read_jsonl(out / "fakeco.partial.jsonl.gz")
    assert "text_error" not in saved[0]  # will be retried on resume


def test_workday_skips_listings_without_link(monkeypatch):
    page = {"total": 2, "jobPostings": [{"title": "No link"},
                                        {"title": "Forward Deployed Engineer", "externalPath": "/job/x_1"}]}

    class FakeResponse:
        def json(self):
            return page

    monkeypatch.setattr(employers, "polite", lambda *a, **k: FakeResponse())
    cfg = {"host": "acme.wd1", "tenant": "acme", "site": "External", "max_per_term": 20}
    results = list(employers.search_workday(cfg, "fde"))
    assert [r["id"] for r in results] == ["/job/x_1"]


def test_partial_file_is_gzip_jsonl(tmp_path):
    path = tmp_path / "x.partial.jsonl.gz"
    employers._write_jsonl(path, [{"id": 1}, {"id": 2}])
    with gzip.open(path, "rt") as fh:
        assert [json.loads(line)["id"] for line in fh] == [1, 2]
