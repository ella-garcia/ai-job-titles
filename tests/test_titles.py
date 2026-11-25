import pytest

from pipeline.titles import seniority, title_norm


@pytest.mark.parametrize("title, expected", [
    ("Senior Solutions Architect (San Francisco)", "solutions architect"),
    ("Sr. Forward Deployed Engineer, Remote", "forward deployed engineer"),
    ("Staff Product Manager — REQ-12345", "product manager"),
    ("Principal Customer Engineer (Hybrid)", "customer engineer"),
    ("Junior Prompt Engineer", "prompt engineer"),
    ("  Design Engineer  ", "design engineer"),
    ("", ""),
    (None, ""),
])
def test_title_norm(title, expected):
    assert title_norm(title) == expected


@pytest.mark.parametrize("title, expected", [
    ("Senior Solutions Architect", "senior"),
    ("Sr. Engineer", "senior"),
    ("Staff Software Engineer", "staff"),
    ("Principal Architect", "principal"),
    ("Intern, Data Science", "intern"),
    ("Junior Product Manager", "junior"),
    ("Lead GTM Engineer", "lead"),
    ("Solutions Architect", None),
    (None, None),
])
def test_seniority(title, expected):
    assert seniority(title) == expected


def test_norm_keeps_family_signal():
    assert "forward deployed" in title_norm("Senior Forward Deployed Architect, Generative AI")
    assert "product manager" in title_norm("Senior or Staff Product Manager, AI Platform")
