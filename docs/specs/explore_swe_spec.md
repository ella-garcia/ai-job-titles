# Spec: FDE against engineering roles (exploratory, Q1)

**Status:** draft, 26 Nov 2026. Not part of frozen protocol v4.
**Purpose:** test whether FDE is a software engineering job placed with the customer, rather than a new job or a renamed SA.
**Proposed module:** `q1_rebrand/explore_swe.py` → `data/runs/q1/explore_swe.json`

## 1. Why

Every rival role tested so far faces customers: SA, Solutions Engineer, technical consultant and support engineer. The terms that pull a posting towards FDE are production, deploy, engineers, build and agent. Ordinary software engineering postings use the same words. So "FDE separates from SA" fits two readings, and the current tests cannot tell them apart:

- **R1. New job:** FDE is distinct from both SA and software engineering.
- **R2. Placed engineer:** FDE is software engineering done at the customer's site, and SA is not its nearest neighbour.
- **R3. Hybrid:** FDE combines SA's customer work with software engineering's delivery, so it separates from each parent.

## 2. New title groups

These groups are labelled from titles only, as in Section 3.3 of the paper, and applied after the existing rules so that no posting changes group.

| Group | Include (title regex, case-insensitive) | Exclude |
| --- | --- | --- |
| Software engineer (SWE) | software engineer, software developer, backend / back-end engineer, frontend / front-end engineer, full-stack / full stack engineer, platform engineer, infrastructure engineer | any title already labelled FDE, SA, consultant, support or PM; forward deployed, solutions, sales, customer, field, support, deployment, implementation, success; manager, director, head of, VP, lead (people-management titles); intern, graduate, new grad; machine learning, ML, AI, data |
| ML / AI engineer | machine learning engineer, ML engineer, AI engineer, applied scientist | applied AI engineer (customer-facing at some AI labs; report separately, see §6); research scientist; the SWE exclusions |
| FDE without strategists | the v4 FDE group minus "deployment strategist" and "forward deployed strategist" | — |

Seniority words (senior, staff, principal) stay in both SWE and FDE.

**Masking:** add the new title phrases to the masking list ("software engineer", "software developer", "backend", "full-stack", "machine learning engineer", "AI engineer" and variants). Otherwise a sentence such as "As a Software Engineer, you will…" gives the label away. Re-check that the FDE masking still removes "forward deployed" before the SWE patterns run. Also mask the bare word "strategist": the frozen list masks only "deployment strategist".

**Data check before running:** count SWE and ML postings per company in the development snapshot (13 Nov). SWE will far outnumber FDE, so the per-company cap of 40 decides the sample. Record the counts in the output file.

## 3. Tests

Use the same pipeline as the frozen tests throughout:
- the same masking, boilerplate removal and de-duplication
- the per-company cap of 40 and class balancing
- TF-IDF on words and word pairs, with logistic regression and C chosen by inner cross-validation
- five outer folds grouped by company
- 2,000 company-bootstrap draws, 200 label shuffles and 10 sampling seeds

| ID | Test | Scope | What it answers |
| --- | --- | --- | --- |
| E1 | FDE vs SWE | all companies; same companies (≥ 8 per class) | Is FDE nearer SWE than SA? |
| E2 | SA vs SWE | all companies | Scale check: two jobs everyone treats as different |
| E3 | FDE vs ML / AI engineer | all companies | Is FDE an AI-engineering job? |
| E4 | Placement (five-way) | out-of-company | Where FDE sits among its neighbours (R1 / R2 / R3) |
| E5 | Headline and all-companies tests without strategists | as in the frozen tests | Do strategist titles pull FDE towards SA? |
| E6 | Strategist vs SA, and strategist vs FDE engineer (added after the first runs) | all companies; same companies | Where do strategist titles sit between SA and FDE engineers? |

Also report the stable terms (top 25 in at least four of five folds) for E1 and E3, as in Table 4 of the paper.

### E4 in detail

1. Train one multinomial logistic regression on five classes: SA, SWE, ML / AI engineer, support engineer and technical consultant. Drop consultant if fewer than 4 companies have 8 or more postings, and record that. No FDE posting enters training.
2. Score every FDE posting with a model whose training excluded that posting's company, using grouped folds.
3. For each class, report the mean predicted probability across FDE postings, the share of FDE postings whose highest probability is that class, and company-bootstrap intervals for both.
4. Repeat steps 1 to 3 for SA postings as a control: SA postings should land mostly on SA.

## 4. Reading rules (fix before running E1 to E4)

The thresholds are our proposal and were not pre-registered. Write them into the output file's header before any run.

**E1, read against the frozen anchors:**
- FDE vs SWE ≤ 0.65 (near the near-synonym anchor of 0.52): **R2**. SWE is FDE's nearest neighbour, and the thesis changes.
- FDE vs SWE ≥ 0.85, and above FDE vs SA on the same scope: **R1** for SWE. FDE is distinct from software engineering.
- Between these: decided by E4.

**E4, using mean probabilities across FDE postings:**
- P(SWE) ≥ 0.60: **R2**.
- P(SA) ≥ 0.60: rebrand reading (contradicts the main result; check labels first).
- P(SA) ≥ 0.25 and P(SWE) ≥ 0.25 and P(SA) + P(SWE) ≥ 0.70: **R3**, a hybrid of SA and SWE.
- No class ≥ 0.40: **R1**. FDE sits away from all five neighbours.
- Anything else: report as unresolved.

**E5:** if dropping strategists moves the all-companies accuracy by more than the seed SD of the headline (0.04 on development), report both versions and discuss.

## 5. Running it so it counts

Development data (13 Nov) is for building and debugging. The frozen held-out snapshots (19, 23 and 25 Nov) have already been read for the main tests. They have not been read for E1 to E5, but we have seen their companies.

1. Build and debug on the 13 Nov snapshot only.
2. Hash this spec, the new title rules and the masking list, as was done for v4. Do this before the next pull.
3. Treat snapshots after that date as the confirmation set for E1 to E5. Report the runs on 19–25 Nov as exploratory.

## 6. Checks and caveats

- **Applied AI Engineer:** at some AI labs this title is customer-facing. Keep it out of the ML group and count it, then read 10 of those postings by hand before deciding where it belongs.
- **Seniority mix:** FDE postings may skew senior. Report the share of senior / staff / principal titles in FDE and SWE, and rerun E1 on senior titles only if the shares differ by more than 20 points.
- **Company mix:** SWE postings come from far more companies than FDE postings. The same-company version of E1 is the controlled comparison, and the all-companies version is context.
- **Hand check:** read 20 FDE postings that E4 places on SWE, and 20 it places on SA, before writing them up.

## 7. Outputs

`data/runs/q1/explore_swe.json` should include:
- the reading rules (copied from §4)
- per-company counts
- accuracy, CI, chance and seed spread for E1, E2, E3 and E5
- the E4 probability table with intervals, plus the SA control
- the stable terms for E1 and E3
- the strategist sensitivity results (E5) and the strategist tests (E6), with E6's comparison against FDE engineer vs SA as its own Holm family
