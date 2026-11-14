# Q1: is a Forward Deployed Engineer a new role or a renamed Solutions Architect?

**Test:** hide the job title and company, and ask whether a classifier can tell FDE postings from Solutions
Architect / Customer Engineer (SA) postings from the work described. Read the result against two anchors
run the same way: near-synonym titles (SA "architect" vs "engineer", expected near chance) and clearly
different roles (SA vs product manager, expected near perfect).

## Steps

| Command | What it does | Status of its numbers |
| --- | --- | --- |
| `make q1` | All tests on the development set (snapshots up to the freeze) | Exploratory |
| `make q1-freeze` | Records the protocol hash, git commit, freeze date and development postings in `frozen/` (commit it) | — |
| `make q1-final` | Scores postings first seen after the freeze; refuses if `protocol.yaml` changed | Held-out |
| `make q1-over-time` | FDE vs SA by period using archived postings (`make archive` first) | Exploratory |

`preview.py` is the first version (one week, fixed C, 20 shuffles), kept for reference.

## Protocol ([protocol.yaml](protocol.yaml))

1. **Corpus** ([data.py](data.py)): boards, big-employer searches and archived postings. HTML stripped,
   boilerplate sentences removed per company and source, postings under 500 characters and non-English
   postings dropped, **title words and company/product names masked**, location copies and repeat weeks
   counted once (by a hash of company and masked text).
2. **Sampling** ([evaluate.py](evaluate.py) `balanced`): at most 40 postings per company per class. The
   headline uses only companies posting both roles (8+ each), with equal numbers from each company.
3. **Model:** TF-IDF on words and word pairs, logistic regression with C chosen from {0.1, 1, 10, 100} by
   inner cross-validation.
4. **Validation:** outer GroupKFold by company, with near-duplicate postings (cosine ≥ 0.95) merged into
   one group, so every test company is unseen in training. The vectorizer is fitted inside each split.
5. **Uncertainty:** 95% interval from 2,000 bootstrap resamples of whole groups; chance level from 200
   label shuffles; the headline repeated with 10 sampling seeds.
6. **Comparisons (pre-registered, one-sided, Holm-corrected):** headline > near-synonym anchor, and
   headline < distinct-roles anchor.
7. **Terms:** words in the top 25 in at least 4 of the 5 outer folds.

## Held-out design

The development set is every snapshot up to the freeze date. The held-out set is postings first seen in
later weekly pulls, excluding every development posting and anything nearly identical to one (a reposted
job). Re-running `make q1-final` with more snapshots (`--rerun`) keeps earlier results with a timestamp.

## Over time ([over_time.py](over_time.py))

1. **SA-likeness:** a model trained on current postings scores every archived FDE and SA posting with
   P(FDE). Lower scores for 2011-22 FDE postings than for today's would mean FDE has moved away from SA.
   Archived SA postings are the control for changes in vocabulary over the years.
2. **Distance:** cosine similarity of the FDE and SA centroids per period, with a company bootstrap.

Archived postings come from a few companies per period, so check the `companies` column before reading a
trend: a period can reflect who was archived as much as how the role changed.
