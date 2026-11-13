import pytest

from pipeline.wayback import is_usable, looks_like_posting, page_title, period_of, strip_html


@pytest.mark.parametrize("url, expected", [
    ("https://jobs.lever.co/scaleai/bf9de512-13e5-4f6d-8320-64c56f498c40", True),
    ("http://www.palantir.com:80/careers/OpenPosDetail?id=a0m80000005LUmSAAW", True),
    ("https://boards.greenhouse.io/anthropic/jobs/4020305008", True),
    ("http://www.palantir.com:80/careers/OpenPosApply?id=a0m80000000gtfM", False),   # apply form
    ("http://www.palantir.com:80/careers/OpenPositionLanding?team=x", False),        # landing page
    ("https://jobs.lever.co/scaleai/bf9de512-13e5-4f6d-8320-64c56f498c40/apply", False),
    ("http://www.palantir.com:80/careers/benefits", False),
])
def test_looks_like_posting(url, expected):
    assert looks_like_posting(url) is expected


@pytest.mark.parametrize("ts, expected", [
    ("20130619174005", "P0"),
    ("20221129235959", "P0"),
    ("20221130000000", "P1"),
    ("20241231120000", "P1"),
    ("20250101000000", "P2"),
    ("20090101000000", None),
])
def test_period_of(ts, expected):
    assert period_of(ts) == expected


def test_strip_html_and_title():
    html = "<html><head><title>Open Positions &amp; Jobs</title><script>var x=1;</script></head>" \
           "<body><h2>Responsibilities</h2><p>Scope deployments</p></body></html>"
    assert page_title(html) == "Open Positions & Jobs"
    text = strip_html(html)
    assert "var x" not in text and "Responsibilities Scope deployments" in text


def test_failed_downloads_are_not_cached(tmp_path, monkeypatch):
    import gzip
    import json

    from pipeline import wayback
    monkeypatch.setenv("AJT_DATA", str(tmp_path))
    path = wayback._cache_dir() / f"{wayback._slug('x.com/jobs')}.pages.jsonl.gz"
    with gzip.open(path, "wt") as fh:
        fh.write(json.dumps({"key": "1|a", "status": 0, "title": "", "chars": 0, "has_resp": False}) + "\n")
        fh.write(json.dumps({"key": "2|b", "status": 200, "title": "FDE", "chars": 900, "has_resp": True}) + "\n")
    assert list(wayback._load_pages("x.com/jobs")) == ["2|b"]


def test_is_usable():
    good = dict(status=200, title="Forward Deployed Engineer", chars=5000, has_resp=True)
    assert is_usable(good)
    assert not is_usable({**good, "has_resp": False})
    assert not is_usable({**good, "chars": 100})
    assert not is_usable({**good, "status": 404})
