# Working together

Two authors, one repo. These rules keep results reproducible and keep scraped text out of a public repo.

## One-time setup (each of us)

1. Get access: the repo owner adds you as a collaborator on `ella-garcia/ai-job-titles` (*Settings → Collaborators*). It is private; code is on `main`, weekly snapshots on the `data` branch.
2. Clone and set up:

   ```bash
   git clone https://github.com/ella-garcia/ai-job-titles.git
   ```

   ```bash
   cd ai-job-titles && make setup
   ```

3. **Get the data:** `make snapshots`. It checks out the `data` branch in `.snapshots/` and copies everything
   collected so far into `./data/raw/`: the weekly board and big-employer snapshots, the Hacker News extract and
   the archived (Wayback) postings. Run it again after each Monday's pull. Nothing else is needed to reproduce the
   results: `make test`, then `make q1`.
4. **`.env` is optional.** `make setup` creates it from `.env.example`, and the defaults work. Fill in only what
   you need:
   - `KAGGLE_USERNAME`, `KAGGLE_KEY`: only to run the Kaggle step. Each of us uses our own token; never share one.
   - `GCP_PROJECT` (then `gcloud auth application-default login`): only to pull Hacker News from BigQuery instead
     of the Hugging Face copy.
   - `AJT_DATA`: only to keep the data somewhere other than `./data`, e.g. a shared Google Drive folder synced with
     [Google Drive for desktop](https://www.google.com/drive/download/), shared by email as Editor (never "anyone
     with the link"). That only saves re-running steps whose output isn't on the `data` branch yet.

## Day to day

- **Branch per task, pull request to `main`.** Name branches after the question: `q1-classifier`, `pipeline-sectioner`. The other author reviews before merging; CI must pass.
- **Pull before you start:** `git pull`, then `uv sync` if `uv.lock` changed. `make snapshots` brings in the latest weekly snapshots.
- **The `data` branch is for data only.** The weekly-pull workflow writes there every Monday. One-off collections
  (Hacker News, archived postings) are added by hand from the `.snapshots/` checkout: copy the files under
  `snapshots/raw/<source>/`, add one row per file to `snapshots/manifest.csv` (with its sha256), commit and push.
  Never put code there, and branch from `main`, not from `data`.
- **Dependencies:** `uv add <package>` (or `uv add --optional analysis <package>`), commit `pyproject.toml` and `uv.lock` together, then regenerate `requirements.txt` for Colab: `uv export --no-hashes --no-dev -o requirements.txt`.
- **Parameters go in `config.yaml`**, not in code.
- **Notebooks are thin.** Anything a figure or number depends on lives in `pipeline/` or `q*/`, with a test.

## Data rules

- **Never commit data to `main`.** `.gitignore` blocks the data folder, Parquet and gzipped JSONL; a pre-commit hook blocks files over 1 MB. Data reaches git only through the weekly workflow, on the `data` branch.
- **Notebook outputs are stripped on commit** (`nbstripout` hook), because a printed posting would end up in the public repo. Don't paste posting text into markdown cells either.
- **One person runs each one-off collection** (`make wayback`, `make archive`, `make hn`, `make kaggle`) and adds
  the output to the `data` branch, so the other gets it with `make snapshots` instead of collecting it again.
  Agree who runs it first (by default, whoever owns the Data workstream).
- **Downloads are logged in `manifest.csv`** automatically. If you add a source by hand, add a row.
- **Example text in the README or article** goes through Presidio masking first (names, emails).

## Who does what

The proposed split is in the research plan (Data, Cleaning, Methods, Validation, Writing). Track tasks as GitHub issues, one per question or pipeline step, assigned to one person.
