from pipeline.sectioner import html_to_text, section_text


def test_section_text_splits_headings():
    text = """
About us
We build tools for developers.

Responsibilities
Ship features with customers.
Deploy models in production.

Qualifications
5+ years of software engineering.
Experience with LLMs.

Benefits
Health insurance and equity.
"""
    parts = section_text(text)
    assert "developers" in parts["text_about"]
    assert "Ship features" in parts["text_resp"]
    assert "LLMs" in parts["text_qual"]
    assert "equity" in parts["text_benefits"]


def test_section_text_fallback_all_in_resp():
    text = "Build agents for customers. Work with sales. Travel to sites."
    parts = section_text(text)
    assert parts["text_resp"] == text
    assert parts["text_about"] == ""
    assert parts["text_qual"] == ""
    assert parts["text_benefits"] == ""


def test_html_to_text_and_sections():
    html = """
    <div><h2>What you'll do</h2><p>Own the deployment.</p>
    <h2>Qualifications</h2><p>Python and ML experience.</p></div>
    """
    parts = section_text(html)
    assert "deployment" in parts["text_resp"]
    assert "Python" in parts["text_qual"]


def test_html_to_text_strips_tags():
    assert "Hello" in html_to_text("<p>Hello <b>world</b></p>")
    assert html_to_text(None) == ""
