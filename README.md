# data branch: weekly job-board snapshots

This branch holds only data. It shares no history with `main` and is written by the
`weekly-pull` workflow (`.github/workflows/weekly-pull.yml` on `main`) every Monday.

```
snapshots/
├── raw/boards/<date>/<system>_<company>.json.gz   # full Greenhouse / Lever / Ashby boards
├── raw/employers/<date>/<employer>.jsonl.gz       # big-employer keyword searches
└── manifest.csv                                   # one row per file: source, URL, sha256, rows
```

**Scraped posting text: never publish this branch.** Before the repo is made public, delete this
branch (or publish a fresh copy of `main` as a new repo instead).

To use the snapshots locally, run `make snapshots` on `main`: it checks this branch out in `.snapshots/`
and copies new files into your `AJT_DATA/raw/`.
