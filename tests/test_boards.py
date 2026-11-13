import gzip
import json

from pipeline.boards import jobs_in, read_snapshot, snapshot_files


def test_read_snapshot_gzipped_and_plain(tmp_path):
    payload = {"jobs": [{"title": "Forward Deployed Engineer"}]}
    plain = tmp_path / "greenhouse_anthropic.json"
    plain.write_text(json.dumps(payload))
    gz = tmp_path / "ashby_openai.json.gz"
    with gzip.open(gz, "wt") as fh:
        fh.write(json.dumps(payload))
    assert read_snapshot(plain) == read_snapshot(gz) == payload


def test_snapshot_files_prefers_gzip(tmp_path):
    (tmp_path / "greenhouse_anthropic.json").write_text("{}")
    with gzip.open(tmp_path / "greenhouse_anthropic.json.gz", "wt") as fh:
        fh.write("{}")
    (tmp_path / "lever_palantir.json").write_text("[]")
    names = [p.name for p in snapshot_files(tmp_path)]
    assert names == ["greenhouse_anthropic.json.gz", "lever_palantir.json"]


def test_jobs_in():
    assert jobs_in("lever", [{"text": "a"}]) == [{"text": "a"}]
    assert jobs_in("ashby", {"jobs": [{"title": "b"}]}) == [{"title": "b"}]
