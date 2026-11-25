import pytest

from pipeline import families as F
from pipeline.config import ROOT
from pipeline.families import family, reload_overrides


@pytest.fixture
def override_csv(tmp_path, monkeypatch):
    path = tmp_path / "family_overrides.csv"
    monkeypatch.setattr(F, "OVERRIDES_PATH", path)
    reload_overrides()
    yield path
    monkeypatch.setattr(F, "OVERRIDES_PATH", ROOT / "pipeline" / "family_overrides.csv")
    reload_overrides()


def test_override_labels_unmatched_title(override_csv):
    override_csv.write_text(
        "title_norm,family,cluster_id,note,decided_by,date\n"
        "platform specialist,sa_ce,1,hand label,test,2026-11-22\n",
        encoding="utf-8",
    )
    reload_overrides()
    assert family("Platform Specialist") == "sa_ce"
    assert family("Senior Platform Specialist (Remote)") == "sa_ce"


def test_override_does_not_override_seed_regex(override_csv):
    override_csv.write_text(
        "title_norm,family,cluster_id,note,decided_by,date\n"
        "solutions architect,pm,1,should be ignored,test,2026-11-22\n",
        encoding="utf-8",
    )
    reload_overrides()
    assert family("Solutions Architect") == "sa_ce"


def test_empty_overrides_file(override_csv):
    override_csv.write_text("title_norm,family,cluster_id,note,decided_by,date\n", encoding="utf-8")
    reload_overrides()
    assert family("Office Manager") == "other"
