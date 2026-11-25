# New role or new name? Testing whether the Forward Deployed Engineer is a rebranded Solutions Architect

**Ella Garcia and Rishi Kashyap**
IE University, MCSBT [verify: course name and session] · November 2026

*Working paper. Results marked exploratory were not pre-registered. All figures come from the project's own result files, listed in Appendix B.*

---

## Abstract

AI companies advertise many new job titles, and a new title does not show that the work is new. This paper tests whether the Forward Deployed Engineer (FDE) is a new role or a Solutions Architect (SA) under another name. We remove job titles and company names from 18,562 job postings and ask whether a classifier can still tell FDE postings from SA postings. We read the result against two anchors: two names for one job, and two clearly different jobs. The method, labels and comparisons were frozen before the test data existed. On held-out postings from 57 companies the model had never seen, it separates FDE from SA with 0.907 accuracy (95% CI 0.87–0.94; chance 0.54). Within the same companies, accuracy is 0.796 on the development set and 0.750 on held-out data, the latter from only three companies. FDE postings describe building software in production, while SA postings describe selling. FDE is its own post-sales engineering job, and SA is its nearest neighbour. In an exploratory check with company descriptions removed, 4.3% of FDE postings read like SA postings. One pre-registered comparison cannot yet be run on held-out data, and we report it as open.

---

## 1. Introduction

A classifier that cannot see a job's title or employer tells Forward Deployed Engineer postings from Solutions Architect postings 91% of the time, on 57 companies it never trained on. That number answers a question that title counts cannot.

The usual way to study new AI jobs is to count titles. Forward Deployed Engineer, GTM Engineer, Deployment Strategist and Prompt Engineer all became common after ChatGPT's release in November 2022. But a count of titles measures what employers choose to call a job. It cannot separate a new role from an old role with a new name, because both produce the same rise in the count. Practitioner commentary reflects the confusion: some diagrams draw the FDE as a circle sitting almost exactly on top of the Solutions Architect [verify: source, The Pragmatic Engineer].

The question has been framed around the wrong object. Titles are labels; postings describe work. We therefore test the text of the posting with its label removed.

**Research question: is the Forward Deployed Engineer a new role, or a Solutions Architect with a new title?**

We ask three sub-questions:

1. With titles and company names hidden, how well can a classifier separate FDE postings from SA postings, compared with two names for the same job and with two clearly different jobs?
2. Does the separation hold on postings and companies that played no part in building the method?
3. Is FDE instead a rename of another neighbouring role: Solutions Engineer, technical consultant or support engineer?

Our thesis is that FDE is a distinct post-sales engineering job whose nearest neighbour is SA. Section 2 sets out the framework, Section 3 the data and Section 4 the method. Section 5 reports results, Section 6 draws them together, Section 7 gives implications, and Section 8 lists the limits.

The paper makes three contributions. It replaces title counts with a test on posting text. It gives accuracy a meaning by reading it against two anchors. It reports a held-out result from a protocol frozen before the test data existed, including the comparisons that failed for lack of data.

## 2. Framework: anchored separability

### 2.1 Why titles are weak evidence

Job titles carry real information. Marinescu and Wolthoff (2020) show that the words in a job title explain much of the variation in posted wages and in who applies [verify: page].

Titles are also chosen by employers, and an employer can rename a role without changing it. Work on job postings in economics therefore tends to read the body text: Deming and Kahn (2018) measure skill requirements from posting text, Hershbein and Kahn (2018) track how requirements change, and Acemoglu et al. (2022) measure AI exposure from the skills listed in vacancies. We follow that practice and treat the title only as a label to be tested.

### 2.2 Separability and its two anchors

We define separability as the accuracy of a classifier that predicts which of two title groups a posting belongs to, from text in which title words and company names have been removed. Separability of 0.50 means the two groups cannot be told apart. Separability of 1.00 means they never overlap.

An accuracy figure alone has no natural scale. A value of 0.80 could mean "nearly the same job" or "quite different jobs", depending on how noisy postings are. We fix the scale with two anchors, run through the identical procedure:

- Near-synonym anchor. SA postings titled "architect" against SA postings titled "engineer" (Solutions Engineer, Customer Engineer, Sales Engineer). These are two names for one job, so separability should sit near chance.
- Distinct anchor. SA postings against product manager (PM) postings. These are clearly different jobs, so separability should be near perfect.

The headline test is FDE against SA within companies that post both. If FDE were a rebrand, the headline would land at the near-synonym anchor. If FDE were an unrelated job, it would land at the distinct anchor. We use these four terms (separability, headline, near-synonym anchor, distinct anchor) with the same meaning throughout.

### 2.3 Pre-registered comparisons

Four one-sided comparisons were fixed before the test data existed, with Holm's (1979) correction across the four:

1. Headline is higher than the near-synonym anchor: FDE is more than a second name for SA.
2. Headline is lower than the distinct anchor: FDE and SA are related jobs.
3. FDE against technical consultants is higher than the near-synonym anchor: FDE is not a renamed consultant.
4. FDE against technical consultants is lower than the headline: FDE is closer to post-sales consultants than to SA.

Fixing hypotheses and analysis before seeing the outcome separates prediction from postdiction (Nosek et al., 2018).

## 3. Data

### 3.1 Sources

Postings come from four kinds of source, all collected through public endpoints with an identified user agent. Posting text is kept on a private branch and is not published.

**Table 1.** Data sources

| Source | What it holds | Size | Used in |
| --- | --- | --- | --- |
| Company job boards (Greenhouse, Lever, Ashby) | Every open job with full text | 62 boards (13 at the first pull, 49 added on 15 Nov 2026) | All tests |
| Large-employer career sites | Keyword searches for target roles | 14 employers (for example Amazon, Microsoft, NVIDIA, Capgemini) | All tests |
| Wayback Machine | Archived postings, 2011–2024 | 2,558 postings, 12 companies | Over-time analysis |
| Hacker News "Who is hiring" | Hiring comments since 2011 | 94,117 comments | Not used in this paper |

Boards are pulled weekly because a live board shows only today's jobs. Snapshots were taken on 13, 19, 23 and 25 November 2026. The scheduled pull of 16 November saved nothing: rate limits on several Workday career sites held the job past its time limit. The held-out data therefore starts on 19 November.

### 3.2 Development and held-out sets

The development set is the 13 November snapshot: 7,706 postings after cleaning. Every method choice was made on it. The held-out set is postings first seen in later snapshots, excluding any posting in the development set and any posting nearly identical to one (cosine similarity of 0.95 or more). It holds 10,856 postings.

Most held-out postings come from the 49 boards added after the freeze. The held-out set therefore tests transfer to new companies more than transfer to new weeks. That makes the all-companies result a strong test, and it leaves few companies for the within-company tests (Section 5.2).

### 3.3 Labels

Postings are labelled from their titles with regular expressions, in a fixed order.

- FDE: forward deployed engineers, architects, scientists and strategists; deployment strategists; agent or AI deployment engineers.
- SA: Solutions Architect, Solutions Engineer, Customer Engineer, Sales Engineer and pre-sales titles.
- Technical consultant: technical consultant, professional services, implementation roles, and delivery or resident Solutions Architects.
- PM: product manager.

Two groups carry "forward deployed" in the title and are kept out of every test. Hybrid titles are forward-deployed product, program and engagement managers, consultants and enablement roles. Non-technical titles are forward-deployed accountants, bankers, recruiters and similar. On the development set the title rules found 465 FDE, 18 hybrid and 9 non-technical postings before cleaning. Hardware roles with "forward deployed" in the title are excluded.

Labels come from titles only. Defining FDE from posting text and then classifying on that text would be circular.

## 4. Method

### 4.1 Text preparation

Five steps stop the classifier from learning anything other than the work described.

- Masking. Title words ("forward deployed", "solutions architect", "consultant" and related forms) and company and product names are removed from the text.
- Boilerplate removal. A sentence that appears in more than 30% of one company's postings is dropped, for companies with at least 10 postings.
- Filtering. Postings under 500 characters after cleaning and non-English postings are dropped.
- De-duplication. Location copies and repeat weeks count once, by a hash of company and masked text.
- Grouping. Near-duplicate postings (cosine similarity of 0.95 or more) share one cross-validation group with their company.

### 4.2 Sampling

Each test takes at most 40 postings per company per class. Within-company tests keep only companies with at least 8 postings of each class and take equal numbers of each class from every company. The all-companies test equalises the two classes overall.

### 4.3 Model and validation

The classifier is logistic regression on TF-IDF features of words and word pairs (Salton & Buckley, 1988), implemented in scikit-learn (Pedregosa et al., 2011). Regularisation strength C is chosen from {0.1, 1, 10, 100} by inner cross-validation. The outer loop is five-fold cross-validation grouped by company, so every test company is unseen in training, and the vectoriser is fitted inside each split.

Grouping matters because postings from one employer share style. Random splits would let the model recognise the employer and report inflated accuracy, a form of leakage (Kaufman et al., 2012; Kapoor & Narayanan, 2023). Blocking by group is the standard remedy for structured data (Roberts et al., 2017).

### 4.4 Uncertainty

Confidence intervals come from 2,000 bootstrap resamples of whole company groups (Efron & Tibshirani, 1993). The chance level is the 95th percentile of accuracy under 200 label shuffles (Ojala & Garriga, 2010). The headline is repeated over 10 sampling seeds. Reported terms are those ranked in the top 25 in at least four of five folds.

### 4.5 The freeze

Protocol version 4 was frozen on 15 November 2026 against the 13 November snapshot. The freeze records a hash of the protocol file, the labelling rules and the masking patterns, and the held-out script refuses to run if the hash changes. Versions 1 to 3 were replaced on 14 and 15 November, before any held-out snapshot existed (Appendix A). The first held-out run used the exact version 4 labels. A later change to title normalisation relabels 3 of 19,861 titles; reruns after it are marked in Section 5.2.

### 4.6 What the evidence can and cannot show

Separability measures whether employers describe two title groups differently. It cannot observe the work itself, pay or career paths. Development-set results informed the method and are exploratory. Only the held-out results test the frozen protocol.

## 5. Results

### 5.1 Development set: FDE sits between the anchors

On the development set the headline separability is 0.796, between the two anchors and closer to the distinct one.

**Table 2.** Development-set results (13 Nov 2026 snapshot; exploratory)

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 294 | 5 | 0.796 | 0.62–0.92 | 0.54 |
| FDE vs SA, all companies | 552 | 21 | 0.850 | 0.77–0.93 | 0.53 |
| SA "architect" vs "engineer" (near-synonym anchor) | 128 | 4 | 0.523 | 0.46–0.61 | 0.58 |
| SA vs PM (distinct anchor) | 276 | 7 | 0.946 | 0.85–0.99 | 0.54 |
| FDE vs technical consultant | 140 | 2 | 0.529 | 0.50–0.57 | 0.56 |

The headline companies are Amazon, Capgemini, Databricks, Salesforce and Snowflake. Across 10 sampling seeds the headline averages 0.822 (SD 0.041).

Both anchors behave as designed. The near-synonym anchor is at chance (0.523 against a chance level of 0.58), and the distinct anchor is near perfect (0.946). The headline exceeds the near-synonym anchor by 0.27 (95% CI 0.07–0.41; Holm p = 0.002) and falls below the distinct anchor by 0.15 (95% CI −0.34 to −0.00; Holm p = 0.043).

The consultant test is a non-result. Only Amazon and Databricks had enough postings of both classes, so each fold trained on one company and tested on the other. The model learned nothing that transferred and scored every posting near 50/50. Comparison 4 is formally significant (−0.27; Holm p = 0.003), but it compares the headline with a test that did not work, so we do not interpret it.

**Assessment:** on the data used to build the method, FDE is more than a second name for SA and less than an unrelated job.

### 5.2 Held-out set: the separation transfers to unseen companies

The frozen protocol separates FDE from SA with 0.907 accuracy across 57 held-out companies.

**Table 3.** Held-out results (snapshots of 19, 23 and 25 Nov 2026; 10,856 postings)

| Test | Postings | Companies | Accuracy | 95% CI | Chance (95th pct) |
| --- | --- | --- | --- | --- | --- |
| FDE vs SA, same companies (headline) | 56 | 3 | 0.750 | 0.69–0.81 | 0.55 |
| FDE vs SA, all companies | 504 | 57 | 0.907 | 0.87–0.94 | 0.54 |
| SA "architect" vs "engineer" (near-synonym anchor) | n/a | 0 | not enough data | n/a | n/a |
| SA vs PM (distinct anchor) | 282 | 8 | 0.950 | 0.92–0.99 | 0.55 |
| FDE vs technical consultant | 50 | 2 | 0.560 | 0.53–0.63 | 0.58 |

*Note.* This is the rerun of 25 November, which uses normalised titles (3 of 19,861 titles differ from version 4). The first held-out run, on 23 November with the exact version 4 labels and two snapshots, gave 0.923 for all companies (95% CI 0.88–0.96; 57 companies).

The all-companies result is the strongest evidence in the paper. It comes from postings and employers that played no part in any method choice, and it is higher than the development figure of 0.850. The distinct anchor replicates at 0.950.

The within-company headline is thin. Only Cloudflare, Databricks and Intercom posted at least 8 FDE and 8 SA postings in the new weeks. Their separability is 0.750, close to the development value of 0.796.

That figure is less certain than its interval implies. The bootstrap interval of 0.69–0.81 resamples only three companies, so it is too narrow to trust. The spread across 10 sampling seeds is the better guide: mean 0.734, SD 0.106, range 0.59–0.89. In the first run, with two companies, the model predicted one class for every posting and scored exactly 0.500.

Two pre-registered comparisons cannot be judged. No company has posted 8 new SA "architect" and 8 new SA "engineer" titles since the freeze, so the near-synonym anchor is missing and comparisons 1 and 3 cannot run. Comparison 2 holds: the headline is 0.20 below the distinct anchor (95% CI −0.27 to −0.14; Holm p = 0.001). Comparison 4 is again significant only because the consultant test is stuck near chance on two companies (Cloudflare and LangChain).

A sensitivity run with a 5% boilerplate threshold gives 0.897 for all companies (95% CI 0.86–0.94; 52 companies). The main result does not depend on leftover company text.

**Assessment:** the separation of FDE from SA **replicates** across companies. The within-company test is **thin**, and comparison 1 is **open**.

### 5.3 What separates the two roles

FDE postings describe building and running software; SA postings describe supporting a sale. The terms that the classifier relies on are stable across folds and across both data sets.

**Table 4.** Terms ranked in the top 25 in at least four of five folds (headline and all-companies tests)

| Towards FDE | Towards SA |
| --- | --- |
| production, deploy, deployment, engineers, delivery, directly, alongside, real world, design build, agent | sales, pre-sales, account, deals, POCs, market, solution, cloud, digital, SAP |

The FDE terms point to work done after a contract is signed, inside the customer's systems and next to the customer's engineers. The SA terms point to work done before it: demonstrations, proofs of concept and account plans.

**Assessment:** the difference is **post-sales engineering** against **pre-sales** support.

### 5.4 Rival roles (exploratory)

FDE might be a rename of a role other than SA. We tested three candidates on the development set, outside the frozen protocol, with the same sampling, model and uncertainty.

**Table 5.** FDE against other roles (development set; exploratory)

| Test | Postings | Companies | Accuracy | 95% CI |
| --- | --- | --- | --- | --- |
| FDE vs Solutions Architect titles, all companies | 444 | 20 | 0.896 | 0.85–0.94 |
| FDE vs Solutions, Customer and Sales Engineer titles, all companies | 408 | 18 | 0.877 | 0.79–0.94 |
| FDE vs Solutions Architect titles, same companies | 230 | 4 | 0.704 | 0.52–0.90 |
| FDE vs Solutions, Customer and Sales Engineer titles, same companies | 156 | 4 | 0.795 | 0.58–0.93 |
| FDE vs support engineers, all companies | 122 | 17 | 0.975 | 0.93–1.00 |
| FDE vs support engineers, same companies | 76 | 3 | 0.961 | 0.81–1.00 |
| Support engineers vs SA, same companies | 34 | 2 | 0.824 | 0.63–1.00 |

FDE is about as far from Solutions Architects as from Solutions Engineers. The within-company gap between 0.704 and 0.795 is not significant (difference 95% CI −0.33 to 0.37), which supports pooling them as SA. Support engineers are further from FDE than SA is: their postings turn on issues, troubleshooting, incidents and root causes.

Customer Engineer cannot be assessed separately. The corpus holds one posting with that title, because its main user, Google Cloud, is not among the sources. Technical consultants remain untested for the reason given in Section 5.1.

**Assessment:** no tested predecessor reads like FDE. The consultant reading is **not yet tested**.

### 5.5 Over time (exploratory)

Archived FDE postings read more like SA postings than today's FDE postings do, while SA postings barely moved. We trained the model on current postings and scored 2,558 archived postings with P(FDE), the model's probability that a posting is FDE.

**Table 6.** Mean P(FDE) by period (1 = reads like FDE, 0 = reads like SA)

| Group | To Nov 2022 | Nov 2022–2024 | Current (Nov 2026) |
| --- | --- | --- | --- |
| FDE, all companies | 0.39 (n = 80; CI 0.25–0.50) | 0.39 (n = 32; CI 0.13–0.40) | 0.67 (n = 379; CI 0.55–0.78) |
| SA, all companies | 0.09 (n = 45) | 0.05 (n = 169) | 0.10 (n = 831) |
| Palantir FDE | 0.39 (n = 73) | 0.40 (n = 27) | 0.51 (n = 78) |
| C3.ai FDE | 0.21 (n = 4) | 0.11 (n = 1) | n/a |
| C3.ai SA | 0.08 (n = 6) | 0.11 (n = 11) | n/a |

The SA rows act as a control for general vocabulary change, and they are flat. The rise in the FDE rows suggests that the FDE role has moved away from SA since 2022.

Three cautions apply. Archived FDE postings are mostly Palantir and archived SA postings mostly Databricks, so each period reflects which companies the archive kept. Archived postings are scored by the full model, while current postings use out-of-fold scores. C3.ai is the only company with both roles in the archive before 2025, and its early FDE postings scored close to its SA postings, but that rests on five FDE postings.

The cosine similarity between FDE and SA centroids rises from about 0.3 before 2025 to 0.71 today. We do not read this as convergence. Before 2025 the two roles come from different companies; today they come from the same companies and share wording.

**Assessment:** FDE content appears to have **changed**, not only its name. The evidence is one archive with uneven company coverage.

### 5.6 Which companies' FDE postings read like SA (exploratory)

Few FDE postings read like SA postings once company descriptions are removed: 4.3% of 624, concentrated in three employers.

The same model can be turned on individual postings. We scored every FDE and SA posting in all four snapshots with P(FDE), using a model that never trained on the posting's own company, and counted FDE postings scoring below 0.4 as SA-like. The cut-off was not pre-registered.

Company descriptions inflate this count. Under the frozen cleaning, 7.8% of 690 FDE postings were SA-like, and Capgemini alone had 16 of its 24. Capgemini uses at least eight versions of its "About Capgemini" paragraph, each below the 30% boilerplate threshold, so none was removed. We therefore added a second cleaning step for this analysis only. A sentence is dropped when it appears in 3 or more of a company's postings and in at least one posting outside the FDE and SA families. A sentence that recruiters, product managers and engineers share describes the employer. Sentences shared only between a company's FDE and SA postings are kept, because they are the evidence the check looks for.

**Table 7.** Share of FDE postings scoring below 0.4, companies with at least 5 FDE postings (all snapshots; exploratory)

| Company | FDE postings | SA-like, frozen cleaning | SA-like, company text removed | Share of text removed |
| --- | --- | --- | --- | --- |
| Cloudflare | 8 | 38% (3 of 8) | 38% (3 of 8) | 8% |
| Capgemini | 15 | 67% (16 of 24) | 27% (4 of 15) | 55% |
| Mistral | 23 | 4% (1 of 23) | 22% (5 of 23) | 9% |
| NVIDIA | 5 | 20% (1 of 5) | 20% (1 of 5) | 12% |
| Cisco | 6 | 17% (1 of 6) | 17% (1 of 6) | 41% |
| ServiceNow | 8 | 13% (1 of 8) | 13% (1 of 8) | 39% |
| Databricks | 59 | 17% (13 of 76) | 7% (4 of 59) | 24% |
| Palantir | 77 | 1% (1 of 81) | 1% (1 of 77) | 11% |
| 18 other companies | 5 to 91 each | 0% to 3% | 0% | 0% to 40% |
| All FDE postings | 624 | 7.8% (of 690) | 4.3% | 18% |

*Note.* The first column counts postings after company text is removed. Counts fall under the second cleaning because postings that become identical or shorter than 500 characters drop out.

Removing company text cut Capgemini's SA-like share from 67% to 27%; more than half of its posting text was company description. Databricks fell from 17% to 7%. The step did not weaken the model: balanced accuracy rose from 0.916 to 0.932, and the share of SA postings scoring above 0.6 stayed near 2%. Amazon, Salesforce, OpenAI and Anthropic have no SA-like FDE postings after the step.

Three employers stand out afterwards: Cloudflare (3 of 8), Capgemini (4 of 15) and Mistral (5 of 23). Mistral's share rose from 4% to 22% when company text was removed, which we have not explained. These counts are small, and a low score shows only that a posting's wording resembles SA postings. Each flagged posting needs a human read before anyone concludes that its title is wrong.

**Assessment:** mislabelled FDE postings are **rare** and **concentrated**. Company descriptions, left in, would have overstated them almost twofold.

## 6. Synthesis

The evidence is strongest where the claim is broadest and weakest where it is most controlled.

**Table 8.** Status of each claim

| Claim | Evidence | Status |
| --- | --- | --- |
| FDE postings differ from SA postings | 0.907 on 57 held-out companies; 0.850 on 21 development companies | **Supported** |
| The difference is post-sales engineering against pre-sales | Stable terms on both data sets | **Supported** |
| FDE differs from SA inside the same company | 0.796 on 5 development companies; 0.750 on 3 held-out companies | **Thin** on held-out data |
| FDE is more separable from SA than two names for one job | +0.27, Holm p = 0.002 on development data; anchor missing on held-out data | **Open** on held-out data |
| FDE is less separable from SA than PM is | −0.15 (development), −0.20 (held-out), both significant | **Supported** |
| FDE is not a renamed support engineer | 0.975 on 17 companies | **Supported**, exploratory |
| FDE is not a renamed technical consultant | Two companies in each data set | **Not tested** |
| The FDE role moved away from SA over time | P(FDE) 0.39 to 0.67; SA flat | **Suggestive** |
| Few FDE postings are SA work under an FDE title | 4.3% of 624 postings score as SA-like, in three employers | **Suggestive**, exploratory |

The paper's main finding is that FDE is a distinct post-sales engineering job, with SA as its nearest neighbour.

## 7. Implications and next steps

The findings change how a new title should be read, and they set the order of the remaining tests.

### 7.1 Implications

1. Job seekers should read the posting before the title. An FDE posting that talks about demos, deals and accounts describes SA work, whatever it is called (Section 5.3). Such postings are rare, about 4% of FDE postings, and concentrated in a few employers (Section 5.6).
2. Employers should expect the FDE title to signal engineering. Across 57 held-out companies the title is attached to production work (Section 5.2), so using it for a pre-sales role sets an expectation that the posting text contradicts.
3. Researchers should not count titles as roles. The masked-text test applies to GTM Engineer, Prompt Engineer and other new titles, each against its own candidate predecessor and its own two anchors (Section 2.2).

### 7.2 Next steps, in order

Each step has a condition that must be met before it runs. The thresholds are our proposal and were not pre-registered.

**Table 9.** Remaining tests and their conditions

| Step | Action | Condition to run | Closes |
| --- | --- | --- | --- |
| 1 | Rerun the held-out protocol with the near-synonym anchor | At least 4 companies with 8 new SA "architect" and 8 new SA "engineer" postings, as on the development set | Comparisons 1 and 3 (Section 5.2) |
| 2 | Rerun the consultant test | At least 4 companies with 8 FDE and 8 technical-consultant postings | The untested consultant reading (Sections 5.1 and 5.4) |
| 3 | Label 150 postings by hand, two annotators, agreement reported as Cohen's kappa | Before any new protocol version is frozen | The unaudited title rules (Section 8) |
| 4 | Apply the test to title growth, duplicate postings and AI-washing | After steps 1 to 3 | The project's remaining research questions |

## 8. Limitations

The results have specific limits. Within-company evidence on held-out data rests on three companies, and its bootstrap interval understates the uncertainty. The near-synonym anchor is missing on held-out data, so the central pre-registered comparison is confirmed only on development data. The consultant test has two companies in each data set and shows nothing either way. Most held-out postings come from boards added after the freeze, so the held-out set tests new companies more than new time periods, and its snapshots span seven days. Labels come from title rules that no human has yet audited against a hand-labelled set. The sources over-represent AI-native firms and a few large employers. Google Cloud, the main user of the Customer Engineer title, is absent, and rate limits left several Workday career sites only partly collected. Posting text is written by employers, so it measures how a job is advertised, not the work as performed. The classifier uses word counts and cannot see pay, seniority or reporting lines. Only English postings are included. The over-time analysis depends on which pages the Wayback Machine kept. The title check uses a cut-off of 0.4 that was not pre-registered, and its per-company counts are small. A title-normalisation change after the freeze altered 3 of 19,861 labels in the held-out rerun.

## 9. Conclusion

Forward Deployed Engineer is not a Solutions Architect under a new name. With titles and employers hidden, the two are separable on companies the model never saw, and the words that separate them describe different work: shipping software into production against supporting a sale. The two roles remain neighbours, less separable from each other than either is from product management. What we cannot yet show on held-out data is the size of the gap inside a single company, because too few companies have posted both roles since the freeze. That test is frozen and waiting for data.

---

## References

Acemoglu, D., Autor, D., Hazell, J., & Restrepo, P. (2022). Artificial intelligence and jobs: Evidence from online vacancies. *Journal of Labor Economics, 40*(S1), S293–S340.

Deming, D., & Kahn, L. B. (2018). Skill requirements across firms and labor markets: Evidence from job postings for professionals. *Journal of Labor Economics, 36*(S1), S337–S369.

Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. Chapman & Hall.

Hershbein, B., & Kahn, L. B. (2018). Do recessions accelerate routine-biased technological change? Evidence from vacancy postings. *American Economic Review, 108*(7), 1737–1772.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*(2), 65–70.

Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns, 4*(9), 100804.

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data, 6*(4), Article 15.

Marinescu, I., & Wolthoff, R. (2020). Opening the black box of the matching function: The power of words. *Journal of Labor Economics, 38*(2), 535–568.

Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences, 115*(11), 2600–2606.

Ojala, M., & Garriga, G. C. (2010). Permutation tests for studying classifier performance. *Journal of Machine Learning Research, 11*, 1833–1863.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830.

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929.

Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. *Information Processing & Management, 24*(5), 513–523.

---

## Appendix A. Protocol history

Every change to the protocol was made before the first held-out snapshot of 19 November 2026.

| Version | Date | Change |
| --- | --- | --- |
| v1 | 14 Nov 2026 | First freeze: headline, two anchors, two comparisons. Development headline 0.815. |
| v2 | 15 Nov 2026 | Adds the technical-consultant test and comparisons 3 and 4. Moves delivery and resident Solutions Architects to technical consultant, adds Sales Engineer to SA and deployment engineers to FDE, excludes hardware roles, and fixes masking of new company names. Development headline 0.854. |
| v3 | 15 Nov 2026 | Non-technical "forward deployed" titles stop counting as FDE. Development headline 0.818. |
| v4 | 15 Nov 2026 | Decides by the title's role word, after v3 dropped real FDE titles that contained industry words. Splits excluded titles into hybrid and non-technical. Development headline 0.796. |

The record of each superseded freeze is kept in `q1_rebrand/frozen/superseded/`.

## Appendix B. Reproducibility

The code is in the project repository; posting text is kept on a private data branch and is not published.

| Step | Command | Output |
| --- | --- | --- |
| Copy the collected data locally | `make snapshots` | `data/raw/` |
| Development results | `make q1` | `data/runs/q1/dev_results.json` |
| Held-out results | `make q1-final` (add `--rerun` after new pulls) | `data/runs/q1/final_results.json` |
| Rival roles | `uv run python -m q1_rebrand.explore_titles` | `data/runs/q1/explore_titles.json` |
| Over time | `make q1-over-time` | `data/runs/q1/over_time.json` |
| Title check | `uv run python -m q1_rebrand.explore_title_check` | `data/runs/q1/title_check.json` |

Settings: per-company cap 40; minimum 8 per class for within-company tests; TF-IDF on 1–2 grams with minimum document frequency 3 and sublinear term frequency; C grid {0.1, 1, 10, 100}; 5 outer and 3 inner folds; 2,000 bootstrap draws; 200 permutations; 10 sampling seeds; seed 42.
