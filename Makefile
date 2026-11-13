PY := uv run python -m pipeline

.PHONY: setup analysis-deps test lint week1 boards employers wayback hn kaggle summary notebook snapshots

setup:            ## install Python 3.11 + pinned deps, git hooks, and a .env to fill in
	uv sync
	uv run pre-commit install
	@test -f .env || (cp .env.example .env && echo "Created .env: fill in AJT_DATA, GCP_PROJECT, KAGGLE_*")

analysis-deps:    ## add the heavier analysis libraries (embeddings, topic models, ...)
	uv sync --extra analysis

test:
	uv run pytest -q

lint:
	uv run ruff check .

# --- Week 1: data collection. Each step skips work already saved today. ---
week1: boards employers wayback hn kaggle summary

boards:           ## full Greenhouse / Lever / Ashby boards (~1 min)
	$(PY) boards

employers:        ## big employers by keyword search (~1 hour, mostly Microsoft)
	$(PY) employers

wayback:          ## Wayback coverage test: the go/no-go gate (~30-60 min)
	$(PY) wayback

hn:               ## HN Who is Hiring (BigQuery, or Hugging Face fallback)
	$(PY) hn

kaggle:           ## Kaggle LinkedIn sets -> Parquet
	$(PY) kaggle

summary:          ## coverage tables + week1_summary.json in runs/<date>/
	$(PY) summary

notebook:
	uv run jupyter lab notebooks/

snapshots:        ## fetch the weekly snapshots (data branch) and copy new files into AJT_DATA/raw
	git fetch -q origin data
	@test -d .snapshots || git worktree add -q --detach .snapshots origin/data
	git -C .snapshots checkout -q --detach origin/data
	$(PY) sync-snapshots
