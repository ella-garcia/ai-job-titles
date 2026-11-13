# AI job titles: new roles or rebrands?

Is a Forward Deployed Engineer a new job, or a Solutions Architect with a new title? We test this with classic NLP on job postings from 2011 to today: embeddings, near-duplicate detection, topic models and classifiers, all validated against a hand-labelled set.

Status: **week 1, data collection.** Findings and charts will appear here.

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

The repo is private for now; we will make it public with the article. Data is never in git. The data folder is set by `AJT_DATA` in `.env`:

```
<AJT_DATA>/
├── raw/          # downloads, by source and date (boards/, employers/, hn/, kaggle_*/)
├── processed/    # cleaned Parquet
├── cache/        # Wayback pages etc., so interrupted runs resume
├── runs/<date>/  # results, plus pip-freeze.txt and git-commit.txt
└── manifest.csv  # one row per download: source, URL, sha256, rows, licence
```

To share data between collaborators, point `AJT_DATA` at a shared Google Drive folder synced with Google Drive for desktop. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Weekly pull

Live job boards only show today's roles, so they are pulled every week by a scheduled GitHub Action. The workflow lives in the private data repo `ella-garcia/ai-job-titles-data`, because its output is scraped text; [ops/weekly-pull.yml](ops/weekly-pull.yml) is the copy kept here. It needs the secret `CODE_REPO_TOKEN` in the data repo (a fine-grained token with read access to this repo).

## Repo layout

```
├── config.yaml        # every parameter: companies, search terms, families, periods, thresholds
├── pipeline/          # collection code (boards, employers, wayback, hn, kaggle, summary)
├── notebooks/         # thin runners; logic stays in pipeline/ and q*/
├── tests/
├── docs/              # data sources, developer notes, GPU/Colab
└── ops/               # weekly-pull workflow for the private data repo
```

Analysis folders (`q1_rebrand/` … `q9_h1b_classification/`, `validation/`, `figures/`) are added as each step starts. Their dependencies install with `make analysis-deps`.

## Docs

- [Data sources](docs/DATA_SOURCES.md): what each source covers and what we found
- [Developer notes](docs/DEVELOPER_NOTES.md): schemas, method defaults, validation, publishing rules
- [GPU and Colab](docs/GPU_AND_COLAB.md): the few steps that need a GPU
- [Contributing](CONTRIBUTING.md): how we work together

## Data and licences

We publish code and aggregates only, never raw posting text. Sources keep their own terms: Indeed Hiring Lab and O\*NET (CC BY 4.0), Stack Overflow survey (ODbL), DOL disclosure data (public). Code is MIT licensed.
