from pathlib import Path

from validation.kappa import agreement


def test_cohen_kappa_perfect_and_disagreement(tmp_path: Path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    a.write_text(
        "posting_id,family_human,ai_bullet,section\n"
        "1,fde,1,ok\n"
        "2,sa_ce,0,ok\n"
        "3,pm,0,bad\n",
        encoding="utf-8",
    )
    b.write_text(
        "posting_id,family_human,ai_bullet,section\n"
        "1,fde,1,ok\n"
        "2,sa_ce,1,ok\n"
        "3,pm,0,ok\n",
        encoding="utf-8",
    )
    result = agreement(a, b)
    assert result["n_shared"] == 3
    assert result["fields"]["family_human"]["kappa"] == 1.0
    assert result["fields"]["ai_bullet"]["n"] == 3
    assert result["fields"]["ai_bullet"]["kappa"] < 1.0
