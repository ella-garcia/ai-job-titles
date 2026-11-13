# Developer notes

Build notes for whoever implements the research plan. The plan says *what* to test; these notes say *how* to build it so results are reproducible, leak-free and safe to publish. Items marked **verify** are from memory or docs and should be checked before relying on them.

## 1. Definition of done

- One command per stage (`make data`, `make clean`, `make q1` … `make figures`) runs end to end from a fresh clone, given the downloads in §3.
- Every chart in `figures/` has a matching CSV of the numbers behind it.
- No raw scraped posting text is committed. Only code, aggregates, and masked examples.
- Golden set labelled by both authors; Cohen's kappa reported.
- README table (question → method → metric) filled in with real results.

## 2. Environment

- Python 3.11, dependencies pinned with `uv` (or `pip-tools`) in `requirements.lock`.
- Core: pandas, pyarrow, scikit-learn, xgboost, sentence-transformers, hdbscan, umap-learn, bertopic, datasketch, rapidfuzz, gensim, nltk (or kenlm), spacy, presidio-analyzer, presidio-anonymizer, waybackpy, google-cloud-bigquery, requests, pyyaml.
- Local first. Only DistilBERT fine-tuning needs a GPU (Colab or Kaggle); embeddings run on an Apple Silicon Mac. See `docs/GPU_AND_COLAB.md`. Every run saves `pip-freeze.txt` and the git commit in `runs/<date>/`.
- Environment: `uv` with `pyproject.toml` + `uv.lock` (Python 3.11); `make setup`. `requirements.txt` is exported from the lock for Colab only.
- All parameters live in `config.yaml` (periods, thresholds, seeds, company list). No magic numbers in code.
- Global seed `42`; pass it to every sampler, model and permutation test.

## 3. Data acquisition

Store everything under `<AJT_DATA>/raw/<source>/<download-date>/`, outside git (`AJT_DATA` is set in `.env`; default `./data`). Each download is logged in `<AJT_DATA>/manifest.csv`: source, URL, date, file, sha256, row count, licence. Collection code is in `pipeline/`; current endpoint status is in `docs/DATA_SOURCES.md`.

| Source | How to get it | Notes |
| --- | --- | --- |
| HN Who is Hiring | BigQuery `bigquery-public-data.hacker_news.full` (query below) | Comments are HTML; unescape and strip tags. One comment can list several roles: split. |
| DOL H-1B LCA | Quarterly/annual disclosure files from the OFLC performance data page (older years via flcdatacenter.com) | Column names change across years (e.g. `LCA_CASE_JOB_TITLE` in FY13 vs `JOB_TITLE` later): keep a column-mapping table in `pipeline/lca_columns.yaml`. Use certified cases only. |
| Wayback CDX | `https://web.archive.org/cdx/search/cdx?url=<board>&matchType=prefix&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=urlkey` | Fetch raw snapshots with `https://web.archive.org/web/<timestamp>id_/<original>`. Max ~1 request/second. `jobs.lever.co/palantir/` has no snapshots before Dec 2020: for the 2011–15 Palantir postings (Q8) use `palantir.com/careers/OpenPosDetail?id=…` and `PositionDetail?id=…` (~370 posting URLs, 2010–16; checked 2026-11-13: full text with Responsibilities, but a generic `<title>`, so parse the job title from the page heading). Companies change systems over time: try each company's Lever, Greenhouse and own-site prefixes. |
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true` | Public, no key. `content` is HTML-escaped. |
| Lever | `GET https://api.lever.co/v0/postings/<company>?mode=json` | Public postings endpoint. Checked 2026-11-13. |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/<org>` | Public job-board endpoint. Checked 2026-11-13. |
| Kaggle LinkedIn | `kaggle datasets download -d arshkon/linkedin-job-postings` and `-d asaniczka/1-3m-linkedin-jobs-and-skills-2024` | Scraped: aggregates only in public outputs. |
| Web Data Commons | JobPosting class-specific subsets (N-Quads) per yearly release | Large; stream-parse, keep only title, hiringOrganization, datePosted, description. Marked optional, but it is the only listed source of pre-2022 full-text postings for non-engineering families (SA, Sales/RevOps, Legal Ops, Designer). The perplexity test, Q6, Q7 and diachronic Word2Vec need that text: either WDC is in v1 or those analyses are cut (see §11). |
| Stack Overflow survey | Yearly zips from survey.stackoverflow.co | `DevType` question wording and options change by year: map options to families by hand. ODbL licence. |
| O*NET | Database zip (text files): Sample of Reported Titles, Alternate Titles, Occupation Data | CC BY 4.0. |
| ESCO | CSV download of occupations + alternative labels | Free. |
| JobBERT | `SentenceTransformer("TechWolf/JobBERT-v2")` (or `-v3` for multilingual) | Titles only; max sequence length 64. |
| Indeed AI Tracker | `github.com/hiring-lab/ai-tracker` CSVs | CC BY 4.0: cite Indeed Hiring Lab. |
| nothiring Spain report | [Tech job market in Spain, Q3 2026](https://nothiring.me/blog/tech-job-market-spain) (recruiting agency, 19,526 jobs, Jul–Sep 2026) | Benchmark to cite, not data: no download. Useful numbers: 75 FDE jobs in Spain (61% describe direct client work); IT services and consulting post 42% of tech jobs and 46% of AI Engineer jobs; 33% of ads relate to AI. Method differs from ours, so compare orders of magnitude only. |

**Weekly live pull:** a scheduled GitHub Actions workflow ([`ops/weekly-pull.yml`](../ops/weekly-pull.yml)) runs `python -m pipeline boards` and `employers` and commits `raw/boards/<date>/` and `raw/employers/<date>/` to the private data repo. Start this in week 1; missed weeks cannot be recovered.

- The workflow lives in, and commits its output to, a **private** repo `ai-job-titles-data`. A git-ignored folder on an Actions runner is deleted when the job ends, and raw text cannot go in the public repo. The weekly commit also keeps the schedule alive (GitHub disables scheduled workflows in public repos after 60 days without activity).
- Board names that respond (checked 2026-11-13). Greenhouse: `anthropic`, `scaleai`, `databricks`, `gleanwork`. Lever: `palantir`. Ashby: `openai`, `cohere`, `sierra`, `harvey`, `snowflake`. Mistral AI was not found under the obvious names.
- Also on these boards: Thoughtworks (consulting) and the VC firms' own roles, a16z (Greenhouse) and Y Combinator (Ashby).
- **Big employers** (Magnificent 7, consulting, large tech, telcos) are not on these three systems. Those with a public search API are searched by role keyword and stored as `raw/employers/<date>/<employer>.jsonl.gz`. Covered: Amazon, Microsoft, Nvidia, Accenture, PwC, Capgemini, Salesforce, Cisco, ServiceNow, AT&T, T-Mobile, Telefónica, Telefónica Tech, Vodafone. Endpoints, pacing and the list of firms not reachable are in `docs/DATA_SOURCES.md` §2. This solves most of the P2 SA / Customer Engineer sample; Google Cloud is the main gap.
- Apple, Google, Meta, Tesla, Deloitte, KPMG, EY, McKinsey, BCG and SAP have no public endpoint or block automated access. Do not work around bot checks; use H-1B LCA filings and the Kaggle LinkedIn sets for them.
- Keyword searches sample a company's postings by search term, unlike the full boards. Do not compare raw counts between the two kinds of source; compare shares within a company.

**HN starting query** (check the result before trusting it):

```sql
WITH threads AS (
  SELECT id, timestamp
  FROM `bigquery-public-data.hacker_news.full`
  WHERE type = 'story' AND `by` = 'whoishiring'
    AND LOWER(title) LIKE 'ask hn: who is hiring%'
)
SELECT c.id, c.parent AS thread_id, t.timestamp AS thread_date, c.text
FROM `bigquery-public-data.hacker_news.full` c
JOIN threads t ON c.parent = t.id
WHERE c.type = 'comment' AND c.text IS NOT NULL
  AND (c.deleted IS NULL OR c.deleted = FALSE)
```

**Scraping etiquette:** respect robots.txt and rate limits; send a User-Agent naming the project and repo URL, not a personal email; cache every response so nothing is fetched twice.

## 4. Unified schemas

Write cleaned data as Parquet in `data/processed/`.

**`postings`** (one row per role, from HN, Wayback, boards, Kaggle, WDC)

| Column | Type | Notes |
| --- | --- | --- |
| posting_id | str | `<source>:<native id>` |
| source | str | hn, wayback, greenhouse, lever, ashby, employer_search, kaggle_li, wdc |
| company | str | Normalised name |
| company_group | str | ai_native, data_software, mag7, consulting, large_tech, telco, vc_accelerator, other |
| spain / language | bool / str | Location in Spain; detected language of the text (non-English excluded from v1 text analyses) |
| title_raw / title_norm | str | `title_norm` = lowercased, seniority/location/team/req-ID stripped |
| seniority | str | intern … principal/staff, from title regex |
| date_posted / date_observed | date | Observed = when we saw it (Wayback timestamp, pull date) |
| period | str | P0 / P1 / P2 (below) |
| role_family | str | sa_ce, fde, pm, ai_pm, designer, so_gtm, legal, prompt, other |
| text_about / text_resp / text_qual / text_benefits | str | Sectioned text; analyses use `text_resp` |
| years_required | float | From regex; null if absent |
| years_ai_required | float | Years stated alongside an AI term (Q5); null if absent |
| url | str | |

**`lca`** (one row per certified H-1B case)

case_id, fiscal_year, decision_date, employer, title_raw, title_norm, role_family, soc_code (6-digit), soc_title, wage_from, wage_to, wage_unit, wage_annual, worksite_state, full_time.

**Periods:** P0 before 2022-11-30 (pre-ChatGPT), P1 2022-11-30 to 2024-12-31, P2 2025-01-01 onward.

## 5. Role-family labelling

1. Seed regexes in `config.yaml` (e.g. `forward[- ]deployed`, `deployment strateg`, `solutions? architect`, `customer engineer`, `gtm engineer`, `legal engineer`, `prompt engineer`, `product manager`, `(product|ux) designer`, `design engineer`).
2. Embed remaining titles with JobBERT, cluster with HDBSCAN, and assign families to clusters by hand.
3. Log every hand decision in `pipeline/family_overrides.csv` so labels are auditable.

## 6. Method defaults

| Step | Defaults | Watch out for |
| --- | --- | --- |
| Boilerplate removal | Drop lines in >30% of a company's postings (company needs ≥10 postings) | Small companies: skip the rule |
| Title clustering | rapidfuzz ratio ≥ 92 to merge spellings; HDBSCAN `min_cluster_size=10` | Check against the JobBERT evaluation set |
| Duplicates (Q3) | MinHash `num_perm=128`, 5-word shingles, Jaccard ≥ 0.8; embedding cosine > 0.95; same company, 30-day window | Shared templates: compare `text_resp` only |
| Classifiers (Q1, Q6) | TF-IDF 1–2 grams, `min_df=3`; logistic regression (C tuned by CV), XGBoost, DistilBERT | **Use GroupKFold by company.** Otherwise the model learns company style, not role. Balance classes by downsampling. |
| Classifier anchors (Q1) | Run the same classifier on two reference pairs: SA vs. Customer Engineer (near-synonyms) and SA vs. PM (clearly distinct) | Read FDE-vs-SA accuracy against these two, not against fixed 55% / 90% marks; without them "partly a rebrand" cannot be proved wrong |
| Title counts (Q2) | Distinct titles per family at a fixed sample size per period (rarefaction: resample to the smallest period's n, 1,000 draws) | Raw distinct counts rise with posting volume. Source mix also changes by period (HN/Wayback in P0, boards in P2): report per source as well as pooled |
| Years of experience (Q5) | Regex for "X+ years"; also `years_ai_required` = years stated in the same sentence as a term from the AI term list | General-experience years say nothing about the hypothesis. Keep a table of first-release dates per technology in `config.yaml` to define "age of the tech" |
| Distance tests | Sentence-transformer centroids; permutation test, 1,000 shuffles | Equalise sample sizes per group |
| N-gram perplexity (Q1, Q7, Q8) | Order 3, Kneser-Ney; train on P0 predecessor postings; report perplexity on held-out P0 predecessor, P2 predecessor and P2 new-title postings | Same vocabulary and similar text lengths across groups; map out-of-vocabulary words to `<unk>` |
| Heaps' law | Fit log V = log K + β log N; bootstrap over postings (1,000) | Compare families at equal N |
| Diachronic Word2Vec | gensim skip-gram, dim 100, window 5, `min_count=10`; align P0 and P2 with orthogonal Procrustes on shared vocabulary | Train several seeds; report drift only if stable across seeds |
| BERTopic | Sentence-level on responsibility bullets; `topics_over_time` | Name topics by hand; fix the random state |
| AI-intensity (Q4) | Cosine to ~20 hand-written AI seed phrases; threshold set on the golden set | Report precision at the chosen threshold |
| H-1B entropy (Q9) | Shannon entropy of 6-digit SOC distribution per title-year; minimum 30 filings | Wage comparison within the same SOC and year only; annualise wages first |

## 7. Validation

- **Golden set:** 150 postings stratified by family × period. Both authors label independently using `validation/labelling_guide.md`, then discuss disagreements.
- **Kappa:** `sklearn.metrics.cohen_kappa_score`; report per field (family, AI-bullet, section).
- **LLM labeller (optional):** save the exact prompt, model name and date in `validation/llm/`; report agreement against the human consensus.
- **Robustness:** re-run Q1 and Q6 with a second embedding model and a second seed; report if conclusions change.
- **Uncertainty:** every chart shows n, plus bootstrap or permutation intervals.

## 8. Privacy, licences and publishing

- `.gitignore` covers `data/`, Parquet and gzipped JSONL; a pre-commit hook blocks files over 1 MB and strips notebook outputs.
- Run Presidio over any example text before it appears in the repo, README or article (HN comments contain names and emails).
- Clear notebook outputs before every commit (install `nbstripout`): a cell that prints a posting puts raw text into the `.ipynb`.
- Publish aggregates, code and download scripts; never redistribute scraped LinkedIn, Wayback or board text.
- Attribution: Indeed Hiring Lab (CC BY 4.0), O*NET (CC BY 4.0), Lightcast (attribution required), Stack Overflow (ODbL: check share-alike terms before publishing derived tables).
- DOL disclosure data is public; employer names are fine to show in aggregate.

## 9. Testing and CI

- Unit tests with small fixtures for: sectioner, title normaliser, years-of-experience regex, HN multi-role splitter, LCA column mapper.
- GitHub Actions: run tests on every push; run the weekly board pull on a schedule.
- Notebooks are for exploration only; anything a figure depends on lives in a module under `q*/` or `pipeline/`.

## 10. Repo layout

```
ai-job-titles/
├── README.md
├── config.yaml
├── Makefile
├── pyproject.toml   # + uv.lock: pinned environment
├── docs/            # data sources, these notes, GPU/Colab
├── ops/             # weekly-pull workflow for the private data repo
├── notebooks/       # thin runners
├── pipeline/        # collect, clean, section, normalise, label families, Presidio
├── q1_rebrand/
├── q2_title_growth/
├── q3_duplicates/
├── q4_ai_washing/
├── q5_requirements/
├── q6_convergence/
├── q7_q8_a16z_test/
├── q9_h1b_classification/
├── validation/
├── extensions/      # RAG demo, CV recommender, gendered wording
├── figures/         # SVG + CSV per chart
└── tests/
```

## 11. Open decisions for the team

- [ ] Final company list for the weekly pull (~30)
- [ ] Whether Web Data Commons is in v1. If not, cut or rescope the perplexity test, Q6, Q7 and diachronic Word2Vec, which have no other pre-2022 text
- [ ] Pass mark for the week-1 coverage gate (suggested: ≥30 usable postings per family per period), covering pre-2022 text for every family, not only Palantir on Wayback
- [ ] Whether to add the two families the big-employer search surfaced (`ai_eng`, `ai_consultant`), or keep them as "other" for v1. The Spain report suggests consulting firms are where most AI hiring sits
- [ ] Whether a Spain comparison (Telefónica, Spain-located postings, the nothiring benchmark) goes in the article or stays a follow-up; non-English text is out of v1 scope
- [ ] Whether to add VC portfolio job boards (e.g. jobs.a16z.com) or keep only the firms' own roles
- [ ] Numeric thresholds for Q2 ("jumped"), Q3 ("more") and Q4 ("many"), committed before any analysis
- [ ] Owners for Q6–Q9, perplexity, Heaps, Word2Vec, DistilBERT and H-1B (not in the plan's work split), or which of them are cut
- [ ] Whether to include the H-1B wage comparison (salary was out of scope in v1)
- [x] GPU source for DistilBERT: local by default, Colab or Kaggle for fine-tuning (docs/GPU_AND_COLAB.md)
- [ ] Repo owner and licence (MIT for code is the usual choice)
