# Q1: is a Forward Deployed Engineer a new role or a renamed Solutions Architect?

**Test:** hide the job title and company, and ask whether a classifier can tell FDE postings from Solutions
Architect / Customer Engineer (SA) postings from the work described. Read the result against two anchors
run the same way: near-synonym titles (SA "architect" vs "engineer", expected near chance) and clearly
different roles (SA vs product manager, expected near perfect). Since protocol v2 the same test is also run
against post-sales technical consultants (professional services, implementation, delivery SAs): the rival
reading that FDE is a renamed consultant rather than a renamed SA.

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
6. **Comparisons (pre-registered, one-sided, Holm-corrected):** headline > near-synonym anchor,
   headline < distinct-roles anchor, consultant > near-synonym anchor, and consultant < headline.
7. **Terms:** words in the top 25 in at least 4 of the 5 outer folds.

## Development-set results (exploratory, protocol v2, snapshot 2026-11-13)

These numbers come from the data used to set up the method, so they are not the result to quote. The
held-out number from `make q1-final` replaces them once the post-freeze pulls are in.

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 314 | 6 | 0.854 | 0.72–0.93 | 0.54 |
| FDE vs SA, all companies | 572 | 21 | 0.872 | 0.81–0.93 | 0.54 |
| SA "architect" vs "engineer" (near-synonym anchor) | 128 | 4 | 0.523 | 0.46–0.61 | 0.58 |
| SA vs product manager (distinct anchor) | 276 | 7 | 0.946 | 0.85–0.99 | 0.54 |
| FDE vs technical consultant | 140 | 2 | 0.543 | 0.50–0.60 | 0.56 |

Pre-registered comparisons (one-sided, Holm-corrected over the four):

- **Headline > near-synonym:** +0.33 (95% CI 0.18–0.43), Holm p = 0.002.
- **Headline < distinct:** −0.09 (95% CI −0.24 to 0.03), Holm p = 0.12, not significant.
- **Consultant > near-synonym:** +0.02 (95% CI −0.08 to 0.12), Holm p = 0.34, not significant.
- **Consultant < headline:** −0.31 (95% CI −0.41 to −0.16), Holm p = 0.002.
- **Across 10 sampling seeds** the headline averages 0.848 (sd 0.030).
- **Stable terms towards FDE:** production, delivery, AI solutions, ps (professional services), environments,
  execution, deploy, agent, design build, scope. **Towards SA:** pre-sales, sales, architectural, workshops,
  account, presentations, cloud.

Reading: FDE is clearly not a renamed pre-sales SA, and its vocabulary is post-sales delivery. On this
development set FDE could not be told apart from technical consultants, **but that test rests on only two
companies (Amazon, Databricks)**: with two companies the cross-validation trains on one and tests on the other,
so near-chance accuracy may mean the FDE-consultant difference does not transfer between those two companies
rather than that the roles are the same. The held-out run adds companies (Cloudflare, MongoDB, GitLab and
others from the 2026-11-15 boards), so it is the real test of the consultant reading.

**Protocol history.** v1 was frozen on 2026-11-14 and superseded by v2 on 2026-11-15, before any post-freeze
snapshot existed. v2 added the consultant comparison and fixed labels and masking: delivery/resident SAs
moved from SA to technical consultant, sales engineers joined SA, agent/AI deployment engineers joined FDE,
and hardware forward-deployed roles were excluded. v1's development results (headline 0.815, distinct
0.977, near-synonym 0.575) and freeze record are in [frozen/superseded/v1](frozen/superseded/v1).

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
