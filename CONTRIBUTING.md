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

3. **Shared data folder.** The owner creates `ai-job-titles-data` in Google Drive and shares it with the other author by email, as Editor (not "anyone with the link"). The other author adds it to My Drive (*right-click → Organise → Add shortcut*). Both install [Google Drive for desktop](https://www.google.com/drive/download/) and set `AJT_DATA` in `.env` to the synced path, e.g.
   `~/Library/CloudStorage/GoogleDrive-<you>@gmail.com/My Drive/ai-job-titles-data`
4. Fill in the rest of `.env`: `GCP_PROJECT` (then run `gcloud auth application-default login`), `KAGGLE_USERNAME`, `KAGGLE_KEY`.

## Day to day

- **Branch per task, pull request to `main`.** Name branches after the question: `q1-classifier`, `pipeline-sectioner`. The other author reviews before merging; CI must pass.
- **Pull before you start:** `git pull`, then `uv sync` if `uv.lock` changed. `make snapshots` brings in the latest weekly snapshots.
- **Never commit to the `data` branch by hand.** Only the weekly-pull workflow writes there. Branch from `main`, not from `data`.
- **Dependencies:** `uv add <package>` (or `uv add --optional analysis <package>`), commit `pyproject.toml` and `uv.lock` together, then regenerate `requirements.txt` for Colab: `uv export --no-hashes --no-dev -o requirements.txt`.
- **Parameters go in `config.yaml`**, not in code.
- **Notebooks are thin.** Anything a figure or number depends on lives in `pipeline/` or `q*/`, with a test.

## Data rules

- **Never commit data to `main`.** `.gitignore` blocks the data folder, Parquet and gzipped JSONL; a pre-commit hook blocks files over 1 MB. Data reaches git only through the weekly workflow, on the `data` branch.
- **Notebook outputs are stripped on commit** (`nbstripout` hook), because a printed posting would end up in the public repo. Don't paste posting text into markdown cells either.
- **Don't run the same collection step at the same time.** Both laptops write to the same Drive folder. Agree who runs `make week1` on a given day (by default, whoever owns the Data workstream).
- **Downloads are logged in `manifest.csv`** automatically. If you add a source by hand, add a row.
- **Example text in the README or article** goes through Presidio masking first (names, emails).

## Who does what

The proposed split is in the research plan (Data, Cleaning, Methods, Validation, Writing). Track tasks as GitHub issues, one per question or pipeline step, assigned to one person.
