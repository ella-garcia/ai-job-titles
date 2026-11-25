# Q4 — AI-washing / AI-intensity

Paper skills layer for v1: **not** a general skill taxonomy. Postings are scored by cosine similarity of sectioned body text (`text_resp` + `text_qual`) to the hand-written phrases in [`seeds.yaml`](seeds.yaml).

## Setup

```bash
uv sync --extra analysis
```

## Seeds and threshold

- Phrases: [`seeds.yaml`](seeds.yaml) (~20 AI skill asks).
- Threshold: `ai_intensity.threshold` in `config.yaml`, set **after** golden-set `ai_bullet` labels using `choose_threshold` (precision subject to `min_recall`).

## Run

Local CSV with a `text` column (and optional `ai_bullet`) under `AJT_DATA` — never commit bodies:

```bash
python -m q4_ai_washing --input data/processed/golden/with_text.csv
```

Scores land in `AJT_DATA/runs/<date>/q4_ai_intensity_scores.csv` (text column dropped).

## Labels

See [`validation/labelling_guide.md`](../validation/labelling_guide.md) for `ai_bullet`.
