PY := uv run python -m pipeline

.PHONY: setup analysis-deps test lint week1 boards employers wayback archive hn kaggle summary notebook snapshots q1 q1-freeze q1-final q1-over-time

setup:            ## install Python 3.11 + pinned deps, git hooks, and a .env to fill in
	uv sync
	uv run pre-commit install
	@test -f .env || (cp .env.example .env && echo "Created .env (optional settings). Next: make snapshots")

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

archive:          ## archived postings (title + text) for comparisons over time (~1-2 hours)
	$(PY) archive

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

# --- Q1: is FDE a new role or a renamed Solutions Architect? (protocol in q1_rebrand/protocol.yaml) ---
q1:               ## development-set results (exploratory): all snapshots up to the freeze
	uv run python -m q1_rebrand.run

q1-freeze:        ## freeze the protocol: commit first; afterwards protocol.yaml must not change
	uv run python -m q1_rebrand.freeze

q1-final:         ## held-out results on postings first seen after the freeze
	uv run python -m q1_rebrand.final

q1-over-time:     ## FDE vs SA by period, using archived postings (run `make archive` first)
	uv run python -m q1_rebrand.over_time
