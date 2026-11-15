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


@pytest.mark.parametrize("title", [
    "Senior Mixed Signal Design Engineer",
    "Senior Physical Design Engineer",
    "Sr. Mechanical Design Engineer, Data Center Design Engineering",
    "Senior ASIC Design Engineer",
    "Innovation and Design Engineer, Worldwide Design Engineering",
])
def test_hardware_design_engineers_are_not_designers(title):
    assert family(title) == "other"


def test_product_design_roles_still_count():
    assert family("Design Engineer") == "designer"
    assert family("Senior or Staff Product Designer, Design Systems") == "designer"


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


@pytest.mark.parametrize("title, expected", [
    ("Forward Deployed Engineer, Professional Services", "fde"),
    ("Agent Deployment Engineer - Spanish Speaking", "fde"),
    ("Deployed Engineer (Atlanta)", "fde"),
    ("Delivery Solutions Architect - Financial Services", "tech_consultant"),
    ("Technical Consultant", "tech_consultant"),
    ("Implementation Engineer", "tech_consultant"),
    ("Enterprise Sales Engineer", "sa_ce"),
    ("Mechanical Engineer - Forward Deployed", "other"),
    ("Forward Deployed Build Engineer", "other"),
])
def test_protocol_v2_labels(title, expected):
    assert family(title) == expected


@pytest.mark.parametrize("title, expected", [
    ("Forward Deployed Accountant", "fd_nontech"),
    ("Forward Deployed Banker, EMEA", "fd_nontech"),
    ("Forward Deployed Recruiter", "fd_nontech"),
    ("Senior Communications Manager, Forward Deployed Engineering", "fd_nontech"),
    ("Forward Deployed Product Manager, Enterprise", "fd_nontech"),
    ("Forward Deployed Process Consultant", "fd_nontech"),
    ("Forward Deployed Engineer", "fde"),
    ("Manager, Forward Deployed Engineering", "fde"),
    ("Forward Deployed Research Scientist", "fde"),
    ("Deployment Strategist", "fde"),
])
def test_protocol_v3_nontechnical_forward_deployed(title, expected):
    assert family(title) == expected
