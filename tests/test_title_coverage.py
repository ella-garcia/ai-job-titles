import pandas as pd

from pipeline.title_coverage import report


def test_report_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("pipeline.title_coverage.load_titles", lambda dates=None: pd.DataFrame())
    monkeypatch.setattr("pipeline.title_coverage.run_dir", lambda: tmp_path)
    monkeypatch.setattr("pipeline.title_coverage.snapshot_dates", lambda: [])
    summary = report([])
    assert summary["postings"] == 0
    assert (tmp_path / "title_coverage_summary.json").exists()


def test_report_writes_aggregates(monkeypatch, tmp_path):
    df = pd.DataFrame({
        "source": ["board", "board", "search"],
        "system": ["greenhouse", "greenhouse", "workday"],
        "company": ["anthropic", "anthropic", "amazon"],
        "group": ["ai_native", "ai_native", "mag7"],
        "title": ["Forward Deployed Engineer", "Office Manager", "Solutions Architect"],
        "title_norm": ["forward deployed engineer", "office manager", "solutions architect"],
        "seniority": [None, None, None],
        "family": ["fde", "other", "sa_ce"],
        "observed": ["2026-11-13"] * 3,
    })
    monkeypatch.setattr("pipeline.title_coverage.load_titles", lambda dates=None: df)
    monkeypatch.setattr("pipeline.title_coverage.run_dir", lambda: tmp_path)
    summary = report(["2026-11-13"])
    assert summary["postings"] == 3
    assert summary["other_postings"] == 1
    assert (tmp_path / "title_coverage_by_family.csv").exists()
    assert (tmp_path / "title_coverage_other_top100.csv").exists()
