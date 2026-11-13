import pytest

from pipeline.families import company_group, family, is_spain


@pytest.mark.parametrize("title, expected", [
    ("Forward Deployed Engineer, AWS Forward Deployed Engineering", "fde"),
    ("Deployment Strategist", "fde"),
    ("Senior Forward Deployed Architect, Generative AI", "fde"),  # fde wins over ai_eng and sa_ce
    ("Principal Solutions Architect (Government)", "sa_ce"),
    ("Customer Engineer, Google Cloud", "sa_ce"),
    ("Arquitecto/a de Soluciones Cloud", "sa_ce"),
    ("Preventa Ciberseguridad", "sa_ce"),
    ("Product Manager, AI Platform", "ai_pm"),
    ("Senior Product Manager", "pm"),
    ("Design Engineer", "designer"),
    ("GTM Engineer", "so_gtm"),
    ("Legal Engineer", "legal"),
    ("Prompt Engineer", "prompt"),
    ("Machine Learning Engineer", "ai_eng"),
    ("Ingeniero/a de Inteligencia Artificial", "ai_eng"),
    ("Consultor/a IA Generativa", "ai_consultant"),
    ("Office Manager", "other"),
    ("", "other"),
    (None, "other"),
])
def test_family(title, expected):
    assert family(title) == expected


def test_ai_needs_word_boundary():
    # 'ai' inside a word ('maintain', 'email') must not count
    assert family("Email Marketing Engineer") == "other"
    assert family("Maintenance Engineer") == "other"


@pytest.mark.parametrize("location, expected", [
    ("Madrid, ES", True),
    ("Spain - Barcelona", True),
    ("Cadiz, Sevilla, Madrid", True),
    ("Tokyo, JPN", False),
    ("Essex, GB", False),
])
def test_is_spain(location, expected):
    assert is_spain(location) is expected


def test_company_group():
    assert company_group("anthropic") == "ai_native"
    assert company_group("a16z") == "vc_accelerator"
    assert company_group("unknown-co") == "other"
