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

### First results (exploratory, full archive collected 2026-11-14)

1,585 archived postings (Palantir, Databricks, OpenAI, Anthropic, Scale AI) against 7,706 current ones.
Only about 300 archived postings are FDE or SA, almost all from Palantir (FDE) and Databricks (SA).

**Same company, then vs now** (mean P(FDE); current postings scored out of fold):

| Company, role | P0 (to Nov 2022) | P1 (Nov 2022–2024) | Today |
| --- | --- | --- | --- |
| Palantir FDE | 0.48 (n=74) | 0.52 (n=27) | 0.61 (n=80) |
| Databricks SA | 0.06 (n=15) | 0.07 (n=173) | 0.10 (n=183) |
| Scale AI FDE | 0.49 (n=2) | 0.46 (n=3) | 0.73 (n=13) |

Current FDE postings across all 18 companies average 0.72 (95% CI 0.62–0.82); current SA, 0.13.

- **FDE moved gradually away from SA; SA stayed put.** Palantir's FDE postings were already distinct from
  SA before ChatGPT and have drifted further towards today's FDE profile. The SA control barely moved.
- **Newer adopters write the role up more distinctly** than Palantir ever did (0.72 vs 0.61).

**Do not read into the centroid distance.** FDE–SA cosine rises from about 0.2 (P0, P1) to 0.71 today
(bootstrap median), but that is mostly company mix: archived FDE is Palantir and archived SA is Databricks,
while today both roles come from the same companies with shared wording.

**Limits.** The archive cannot test whether FDE absorbed SA work: no company posted both roles before 2025
in the archive. Archived pages are scored by the full model while current postings use out-of-fold
scores, and archived text comes from scraped pages rather than board APIs, so the then-vs-now gap is
approximate.
