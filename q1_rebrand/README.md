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

## Development-set results (exploratory, protocol v4, snapshot 2026-11-13)

These numbers come from the data used to set up the method, so they are not the result to quote. The
held-out number from `make q1-final` replaces them once the post-freeze pulls are in.

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 294 | 5 | 0.796 | 0.62–0.92 | 0.54 |
| FDE vs SA, all companies | 552 | 21 | 0.850 | 0.77–0.93 | 0.53 |
| SA "architect" vs "engineer" (near-synonym anchor) | 128 | 4 | 0.523 | 0.46–0.61 | 0.58 |
| SA vs product manager (distinct anchor) | 276 | 7 | 0.946 | 0.85–0.99 | 0.54 |
| FDE vs technical consultant | 140 | 2 | 0.529 | 0.50–0.57 | 0.56 |

Headline companies: Amazon, Capgemini, Databricks, Salesforce, Snowflake.

Pre-registered comparisons (one-sided, Holm-corrected over the four):

- **Headline > near-synonym:** +0.27 (95% CI 0.07–0.41), Holm p = 0.002.
- **Headline < distinct:** −0.15 (95% CI −0.34 to −0.00), Holm p = 0.043.
- **Consultant > near-synonym:** +0.01 (95% CI −0.09 to 0.08), Holm p = 0.40, not significant.
- **Consultant < headline:** −0.27 (95% CI −0.40 to −0.09), Holm p = 0.003.
- **Across 10 sampling seeds** the headline averages 0.822 (sd 0.041).
- **Stable terms towards FDE:** production, engineers, delivery, directly, deploy, alongside, AI solutions,
  design build. **Towards SA:** sales, pre-sales, account, mobile, market, digital, SAP, data analytics.

**"Forward deployed" titles that are not FDE.** Titles are grouped by their role word, not by industry words
("FDE, Legal" is an FDE). On the development set: 465 FDE postings, 18 `fd_hybrid` (product, program and
engagement managers, consultants, enablement) and 9 `fd_nontech` (finance engineers, recruiter,
communications, GRC). Both groups stay out of every test. Hybrids are judged by their requirements only in
exploratory work: using text to define FDE and then classifying on text would be circular.

Reading: FDE is clearly not a renamed pre-sales SA, and its vocabulary is post-sales delivery. On this
development set FDE could not be told apart from technical consultants, **but that test rests on only two
companies (Amazon, Databricks)**: with two companies the cross-validation trains on one and tests on the other,
and the model learned nothing that transferred (every posting scored about 50/50). It is a non-result, not
evidence that the roles are the same. The held-out run adds companies, so it is the real test.

**Which FDE postings read like SA (exploratory, v2 labels).** In the all-companies test 13% of FDE postings
scored below 0.4. Capgemini supplied 16 of those 37 (80% of its FDE postings); elsewhere the share was about
8%, and almost none at OpenAI, Anthropic, Scale AI or Cohere. At Capgemini and Salesforce the FDE postings are
closer to the same company's SA postings (centroid cosine 0.79) than to FDE postings elsewhere (0.34–0.39).
Part of Capgemini's result is leftover "About Capgemini" text: it uses at least eight versions of that
paragraph, each under the 30% boilerplate threshold, so none is removed. A sensitivity run with a 5% threshold
lowered Capgemini's SA-like share to 35–45% and moved the headline from 0.854 to 0.895. The frozen threshold
was not changed after seeing this; the held-out report should include the same sensitivity run.

**FDE against each SA title type and against support engineers (exploratory, outside the frozen protocol).**
[explore_titles.py](explore_titles.py) splits the SA group by title and adds post-sales technical support
(Support Engineer, Customer Success Engineer, Technical Support; internal IT support left out), with the same
sampling, model and uncertainty as the frozen tests. The support group's title words are masked too. Its labels
live in that file, so the frozen protocol is unchanged.

| Test (development set) | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, pooled (frozen headline, re-run) | 294 | 5 | 0.796 | 0.62–0.92 | 0.55 |
| FDE vs Solutions Architect titles, same companies | 230 | 4 | 0.704 | 0.52–0.90 | 0.54 |
| FDE vs Solutions / Customer / Sales Engineer titles, same companies | 156 | 4 | 0.795 | 0.58–0.93 | 0.57 |
| FDE vs Solutions Architect titles, all companies | 444 | 20 | 0.896 | 0.85–0.94 | 0.54 |
| FDE vs Solutions / Customer / Sales Engineer titles, all companies | 408 | 18 | 0.877 | 0.79–0.94 | 0.54 |
| FDE vs support engineers, same companies | 76 | 3 | 0.961 | 0.81–1.00 | 0.57 |
| FDE vs support engineers, all companies | 122 | 17 | 0.975 | 0.93–1.00 | 0.56 |
| Support engineers vs SA, same companies | 34 | 2 | 0.824 | 0.63–1.00 | 0.62 |

- **FDE is about as far from Solutions Architects as from Solutions Engineers.** The same-company gap
  (0.70 vs 0.80) is not significant (difference 95% CI −0.33 to 0.37), and across all companies both are near
  0.88–0.90. Pooling them in the frozen SA group is therefore reasonable. Customer Engineer itself is almost
  absent (one posting): its main user, Google Cloud, is not a source.
- **FDE is not a renamed support engineer.** FDE vs support is near perfect, above the near-synonym anchor
  (+0.44, Holm p = 0.002) and, if anything, further apart than FDE vs SA. Stable terms towards support:
  issues, troubleshooting, incident, root cause, resolution; towards FDE: production, build, deployments, agent.
- **Small samples:** the same-company support tests rest on two or three companies (Amazon, OpenAI, Snowflake).

**Protocol history.** v1 was frozen on 2026-11-14 and superseded by v2 on 2026-11-15, before any post-freeze
snapshot existed. v2 added the consultant comparison and fixed labels and masking: delivery/resident SAs
moved from SA to technical consultant, sales engineers joined SA, agent/AI deployment engineers joined FDE,
and hardware forward-deployed roles were excluded. v1's development results (headline 0.815, distinct
0.977, near-synonym 0.575) and freeze record are in [frozen/superseded/v1](frozen/superseded/v1). v3 replaced
v2 the same day, also before any post-freeze snapshot: non-technical "forward deployed" titles (accountant,
banker, recruiter, PM, consultant and similar) stopped counting as FDE and became their own family,
`fd_nontech`, left out of every test. v2's results (headline 0.854, consultant 0.543) and record are in
[frozen/superseded/v2](frozen/superseded/v2). v4 replaced v3 the same day, before any post-freeze snapshot:
v3 read industry words as roles and dropped real FDEs ("FDE, Legal", "FDE - Communications", Capgemini's
"Consultant, FDE" grade). v4 decides by the role word and splits the excluded titles into `fd_nontech` and
`fd_hybrid`. v3's results (headline 0.818) and record are in [frozen/superseded/v3](frozen/superseded/v3).

## Held-out design

The development set is every snapshot up to the freeze date. The held-out set is postings first seen in
later weekly pulls, excluding every development posting and anything nearly identical to one (a reposted
job). Re-running `make q1-final` with more snapshots (`--rerun`) keeps earlier results with a timestamp.

The first scheduled pull after the freeze (2026-11-16) saved nothing: Workday career sites rate-limited the
big-employer step until the job hit its time limit, and the only commit step came last. The workflow now
commits the boards first and time-boxes the employers. The held-out set therefore starts on 2026-11-19.

## Held-out results (protocol v4, snapshots 2026-11-19 and 2026-11-23, run 2026-11-25)

10,169 postings first seen after the freeze, most of them from the 49 boards added on 2026-11-15, so most
held-out companies were never in the development set.

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 40 | 2 | 0.500 | 0.50–0.50 | 0.60 |
| FDE vs SA, all companies | 466 | 57 | 0.923 | 0.88–0.96 | 0.54 |
| SA "architect" vs "engineer" (near-synonym anchor) | — | — | not enough data | | |
| SA vs product manager (distinct anchor) | 268 | 8 | 0.948 | 0.93–0.99 | 0.55 |
| FDE vs technical consultant | 50 | 2 | 0.560 | 0.53–0.63 | 0.58 |

- **FDE vs SA across 57 companies: 0.923.** On postings and companies never used to set up the method, a
  classifier that cannot see the title tells FDE from SA almost as well as SA from PM. The separating terms
  match the development set: production, engineer, delivery, deployment, code, real world towards FDE; sales,
  pre-sales, account, deals, POCs towards SA.
- **The same-company tests have not run properly yet.** Only Cloudflare and Databricks posted 8+ of each role
  in the new weeks. With two companies the model trains on one and tests on the other; it learned nothing
  that transferred and predicted one class for everything (exactly 0.500; over 10 sampling seeds 0.62, sd
  0.09). The consultant test failed the same way, and no company had enough new architect and engineer SA
  postings for the near-synonym anchor.
- **So the pre-registered comparisons cannot be judged yet.** Two of the four need the near-synonym anchor.
  "Headline < distinct" is formally significant (Holm p = 0.001) only because the headline is stuck at 0.50,
  and "consultant < headline" is not significant. These are non-results, not evidence either way.
- **Next:** `make q1-final --rerun` as weekly pulls add postings, until the same-company tests reach the
  number of companies the development set had (four or five).

**Rerun with the 2026-11-25 snapshot (boards, plus Amazon, Capgemini and Salesforce; the other employers
stopped at Workday rate limits).** 10,856 held-out postings. Earlier results are kept with a timestamp in
`data/runs/q1/`. This rerun uses the normalised titles from PR #16 (below).

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 56 | 3 | 0.750 | 0.69–0.81 | 0.55 |
| FDE vs SA, all companies | 504 | 57 | 0.907 | 0.87–0.94 | 0.54 |
| SA "architect" vs "engineer" (near-synonym anchor) | — | — | not enough data | | |
| SA vs product manager (distinct anchor) | 282 | 8 | 0.950 | 0.92–0.99 | 0.55 |
| FDE vs technical consultant | 50 | 2 | 0.560 | 0.53–0.63 | 0.58 |

- **The headline now runs, thinly.** Intercom joined Cloudflare and Databricks, and FDE vs SA within the same
  companies is 0.75, close to the development set's 0.80. Its interval is too narrow to trust: the bootstrap
  resamples whole companies and there are only three. The 10 sampling seeds give the honest spread: mean
  0.73, sd 0.11 (0.59 to 0.89).
- **Headline < distinct holds** (−0.20, Holm p = 0.001): FDE is less separable from SA than PM is, as on the
  development set.
- **"Consultant < headline" (Holm p = 0.001) is not evidence:** the consultant test is still the two-company
  non-result near 0.50.
- **Headline > near-synonym, the main comparison, still cannot run.** Even with Amazon and Capgemini, no
  company has posted 8+ new SA "architect" and 8+ new SA "engineer" titles since the freeze; most of their SA
  postings were already in the development set.
- **All companies:** 0.907 (57 companies).

**Boilerplate sensitivity (exploratory, 5% threshold instead of 30%):** all companies 0.897 (0.86–0.94, 52
companies), distinct 0.966, headline 0.554 (still two companies). The all-companies result does not depend on
leftover company boilerplate.

**Labels for reruns.** PR #16 (title taxonomy) normalises titles before matching. It leaves the frozen
patterns and hash unchanged but labels 3 of 19,861 current titles differently from v4: two Solution
Architect titles become SA and "Senior People Partner | Legal, Operations & People" becomes legal (it should
stay other). This first held-out result was computed before the merge, with the exact v4 labels; reruns use
the normalised titles and must say so. Hand overrides added to `pipeline/family_overrides.csv` change the
hash, after which `make q1-final` refuses to run until a new protocol version is frozen.

## Over time ([over_time.py](over_time.py))

1. **SA-likeness:** a model trained on current postings scores every archived FDE and SA posting with
   P(FDE). Lower scores for 2011-22 FDE postings than for today's would mean FDE has moved away from SA.
   Archived SA postings are the control for changes in vocabulary over the years.
2. **Distance:** cosine similarity of the FDE and SA centroids per period, with a company bootstrap.

Archived postings come from a few companies per period, so check the `companies` column before reading a
trend: a period can reflect who was archived as much as how the role changed.

### Results (exploratory, protocol v4 labels, archive collected 2026-11-14/15)

2,558 archived postings from 12 companies (Palantir, Databricks, OpenAI, Anthropic, Scale AI, C3.ai,
SingleStore, Cloudflare, Anduril, Braze, Baseten, Clay) against 7,706 current ones. Only 330 archived postings
are FDE or SA. The archived pages are kept on the `data` branch (`snapshots/raw/wayback/`).

**Same company, then vs now** (mean P(FDE); current postings scored out of fold):

| Company, role | P0 (to Nov 2022) | P1 (Nov 2022–2024) | Today |
| --- | --- | --- | --- |
| C3.ai FDE | 0.21 (n=4) | 0.11 (n=1) | — |
| C3.ai SA | 0.08 (n=6) | 0.11 (n=11) | — |
| Palantir FDE | 0.39 (n=73) | 0.40 (n=27) | 0.51 (n=78) |
| Databricks SA | 0.08 (n=14) | 0.04 (n=140) | 0.07 (n=153) |
| Scale AI FDE | 0.46 (n=2) | 0.43 (n=3) | 0.67 (n=11) |

All archived FDE postings average 0.39 in P0 (95% CI 0.25–0.50) and in P1; current FDE postings across 17
companies average 0.67 (0.55–0.78). Archived SA postings average 0.09 (P0) and 0.05 (P1); current SA, 0.10.

- **FDE moved away from SA; SA stayed put.** Palantir's FDE postings drifted towards today's FDE profile, and
  the SA control barely moved.
- **C3.ai is the only company with both roles in the archive before ChatGPT.** Its early FDE postings read
  almost like its SA postings (0.21 vs 0.08, then both 0.11), several of them titled "Forward Deployed
  Solution Engineer / Sales Engineer". This fits FDE content changing rather than only the name, but it rests
  on five FDE postings: a lead, not a finding. C3.ai has no current board in the data, so there is no "today".
- **Newer adopters write the role up more distinctly** than Palantir (0.67 vs 0.51).

**Do not read into the centroid distance.** FDE–SA cosine rises from about 0.3 (P0, P1) to 0.71 today
(bootstrap median), mostly because of company mix: archived FDE is mainly Palantir and archived SA mainly
Databricks, while today both roles come from the same companies with shared wording.

**Limits.** Anduril's archived URLs carry only an ID, so its 200 pages were sampled without seeing titles and
none was an FDE posting; Braze had none either, and Baseten's three were dropped by the corpus filters. 27 pages failed
to download (Archive refusals) and will be retried. Archived pages are scored by the full model while current
postings use out-of-fold scores, and archived text comes from scraped pages rather than board APIs, so the
then-vs-now gap is approximate. Earlier numbers (v1 labels, five companies) put Palantir at 0.48 / 0.52 / 0.61.
