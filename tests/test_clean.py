import pandas as pd

from pipeline.clean import remove_boilerplate, sentences


def test_sentences_split_on_punctuation_and_bullets():
    assert sentences("Build agents. Ship to production! • Work with customers") == [
        "Build agents.", "Ship to production!", "Work with customers"]


def test_boilerplate_removed_only_for_companies_with_enough_postings():
    boiler = "We are an equal opportunity employer. About Acme: we build things."
    duties = ["deploy agents", "run workshops", "write code", "lead demos", "own delivery", "scope projects",
              "train models", "support sales", "design systems", "fix outages", "review contracts", "hire engineers"]
    acme = [f"{boiler} You will {d} with customers." for d in duties]
    tiny = [f"{boiler} You will {d}." for d in duties[:3]]
    df = pd.DataFrame({"company": ["acme"] * 12 + ["tiny"] * 3, "source": "board", "text": acme + tiny})
    out = remove_boilerplate(df, share=0.3, min_docs=10)
    assert out.iloc[0] == "You will deploy agents with customers."
    assert "equal opportunity" in out.iloc[12]          # tiny company: left as is


def test_numbers_are_normalised():
    # "Posted 3 days ago" and "Posted 5 days ago" are the same boilerplate line
    df = pd.DataFrame({"company": "acme", "source": "board",
                       "text": [f"Posted {i} days ago. Unique duty {w}." for i, w in enumerate("abcdefghijkl")]})
    out = remove_boilerplate(df, share=0.3, min_docs=10)
    assert all("Posted" not in t for t in out)
