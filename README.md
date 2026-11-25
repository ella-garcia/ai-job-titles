# AI job titles: new roles or rebrands?

Is a Forward Deployed Engineer a new job, or a Solutions Architect with a new title? We test this with classic NLP on job postings from 2011 to today: embeddings, near-duplicate detection, topic models and classifiers, all validated against a hand-labelled set.

Status: **weekly pulls running; Q1 held-out results in.** Charts will appear here.

**Findings so far (Q1, details in [q1_rebrand/README.md](q1_rebrand/README.md)):**
- **FDE is not a renamed pre-sales Solutions Architect.** With titles and company names hidden, a classifier
  tells FDE from SA postings with 0.92 accuracy across 57 companies it never saw during development (chance
  about 0.54; SA vs product manager 0.95). FDE postings talk about production, deployment and code; SA
  postings about sales, accounts, deals and proofs of concept.
- **The within-company test needs more weeks.** Only two companies posted enough of both roles since the
  freeze, so the pre-registered comparison against near-synonym titles cannot be judged yet. On the
  development set it held (0.80 vs 0.52, Holm p = 0.002).
- **Nor is FDE a renamed support engineer** (0.96–0.98, exploratory). The technical-consultant comparison is
  still a non-result (two companies).
- **Over time (exploratory):** archived FDE postings from before ChatGPT read more like SA (P(FDE) about 0.39)
  than today's (0.67), while SA postings barely moved. C3.ai, the one company with both roles in the archive,
  had early FDE postings close to its SA postings, but that rests on five postings.

| Question | Method | Evaluation |
| --- | --- | --- |
| Q1 Rebrand? | Classifiers, embedding distance, n-gram perplexity | Cross-validated F1, permutation p-value, perplexity ratio |
| Q2 Title growth | JobBERT + HDBSCAN, Heaps' law | Cluster purity, fitted β per family |
| Q3 Duplicates | MinHash / LSH | Precision / recall on hand-labelled pairs |
| Q4 AI-washing | Skill matching, AI-intensity | Precision on the golden set |
| Q5 Requirements | Years-of-experience extraction | Spot-check accuracy |
| Q6 Convergence | Cross-family distance, Word2Vec drift | Distance trend + CI, 3-way classifier accuracy |
| Q7–Q8 a16z test | Distance + perplexity vs. predecessors | Position relative to predecessor spread |
| Q9 H-1B classification | Title → SOC code entropy | Entropy vs. classic titles |

## Quick start

Needs [uv](https://docs.astral.sh/uv/) (`brew install uv`). It installs the right Python (3.11) itself.

```bash
git clone https://github.com/ella-garcia/ai-job-titles.git
```

```bash
cd ai-job-titles && make setup
```

`make setup` installs the pinned environment, the git hooks, and creates `.env`. Fill in `.env` (see [.env.example](.env.example)), then:

```bash
make test
```

```bash
make week1
```

`make week1` runs every collection step: `boards`, `employers`, `wayback`, `hn`, `kaggle`, `summary`. Each can be run alone (`make boards`), and each skips work already saved today. To work interactively, `make notebook` opens [notebooks/01_week1_data.ipynb](notebooks/01_week1_data.ipynb), which calls the same functions.

## Where the data lives

The repo is private for now; we will make it public with the article. Data is never on `main`; collected data is kept on the `data` branch (below). The local data folder is `./data`, or `AJT_DATA` in `.env`:

```
<AJT_DATA>/
├── raw/          # downloads, by source and date (boards/, employers/, hn/, kaggle_*/)
├── processed/    # cleaned Parquet
├── cache/        # Wayback pages etc., so interrupted runs resume
├── runs/<date>/  # results, plus pip-freeze.txt and git-commit.txt
└── manifest.csv  # one row per download: source, URL, sha256, rows, licence
```

Collaborators share data through the `data` branch: `make snapshots` copies it into `raw/`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Weekly pull

Live job boards only show today's roles, so a scheduled GitHub Action ([weekly-pull.yml](.github/workflows/weekly-pull.yml)) pulls the boards and big employers every Monday and commits them to the **`data` branch** of this repo. That branch holds only snapshots and shares no history with `main`, so code work never touches it. Run it by hand from *Actions → weekly-pull → Run workflow*.

One-off collections are kept there too: the Hacker News extract (`raw/hn/`) and the archived postings (`raw/wayback/`). To use them locally, run `make snapshots`: it checks out the `data` branch in `.snapshots/` (git-ignored) and copies new files into your `AJT_DATA/raw/`. It never overwrites a file you already have.

**Before this repo is made public, delete the `data` branch** (it holds scraped posting text), or publish a fresh copy of `main` as a new public repo.

## Repo layout

```
├── config.yaml        # every parameter: companies, search terms, families, periods, thresholds
├── pipeline/          # collection code (boards, employers, wayback, hn, kaggle, summary)
├── notebooks/         # thin runners; logic stays in pipeline/ and q*/
├── tests/
└── docs/              # data sources, developer notes, GPU/Colab
```

Analysis folders (`q1_rebrand/` … `q9_h1b_classification/`, `validation/`, `figures/`) are added as each step starts. Their dependencies install with `make analysis-deps`.

## Docs

- [Data sources](docs/DATA_SOURCES.md): what each source covers and what we found
- [Developer notes](docs/DEVELOPER_NOTES.md): schemas, method defaults, validation, publishing rules
- [GPU and Colab](docs/GPU_AND_COLAB.md): the few steps that need a GPU
- [Contributing](CONTRIBUTING.md): how we work together

## Data and licences

We publish code and aggregates only, never raw posting text. Sources keep their own terms: Indeed Hiring Lab and O\*NET (CC BY 4.0), Stack Overflow survey (ODbL), DOL disclosure data (public). Code is MIT licensed.
