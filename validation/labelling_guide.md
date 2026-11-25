# Golden-set labelling guide

Both authors label the same 150 postings independently, then discuss disagreements. Report Cohen’s κ per field (`family`, `ai_bullet`, `section` when sectioner checks are in scope).

Postings are sampled stratified by **family × period** into `AJT_DATA/processed/golden/` (git-ignored). Do **not** paste raw posting body text into the repo, README, or this guide.

## Field: `family`

Choose one label from the paper role families (same names as `config.yaml`):

| Label | Include | Exclude |
| --- | --- | --- |
| `fde` | Forward Deployed Engineer / Architect / Strategist; Agent/AI Deployment Engineer | Hardware/build “forward deployed”; FD titles that are clearly banker/recruiter/etc. |
| `fd_nontech` | Forward-deployed titles whose role word is non-tech (banker, recruiter, GRC, …) | Software/AI FDE |
| `fd_hybrid` | Forward-deployed PM / consultant / enablement / analyst — ambiguous from the title alone | Clear FDE or clear non-tech FD |
| `tech_consultant` | Technical consultant, professional services, implementation engineer, delivery/resident SA | Pre-sales SA / CE |
| `sa_ce` | Solutions Architect, Customer Engineer, Solutions Engineer, pre-sales / preventa | Delivery/resident SA (those are `tech_consultant`) |
| `ai_pm` | Product Manager with AI in the title | PM without AI |
| `pm` | Product Manager | AI PM |
| `designer` | Product / UX designer, (software) design engineer | ASIC / mechanical / data-center design engineer → `other` |
| `so_gtm` | GTM engineer, RevOps, strategy & operations | Ordinary sales AE without ops/GTM eng |
| `legal` | Legal engineer / legal ops | Ordinary counsel without eng/ops |
| `prompt` | Prompt engineer | — |
| `ai_eng` | AI / ML / LLM / GenAI engineer (kept in v1; see DEVELOPER_NOTES §11) | Generic “software engineer” with no AI term |
| `ai_consultant` | AI / GenAI consultant | Non-AI technical consultant |
| `other` | Everything else | — |

**Rule:** label from the **title** (and `title_norm`), not from how AI-heavy the body looks. Body AI content is the `ai_bullet` field.

If the seed regex in `config.yaml` disagrees with your reading, keep your human label and note it; family overrides / regex fixes are a separate PR.

## Field: `ai_bullet`

Binary for Q4 AI-washing / AI-intensity:

| Value | Meaning |
| --- | --- |
| `1` | The posting asks for concrete AI/ML/LLM work (build, deploy, evaluate, or integrate models/agents) in responsibilities or requirements — not just a buzzword in the company blurb |
| `0` | No substantive AI skill ask; “AI” only in company mission, product name, or marketing |

Ignore the job title when judging `ai_bullet` (a classic SA title can still be AI-heavy; an “AI Engineer” title can still be washed). Prefer `text_resp` / `text_qual` from the sectioner when available.

## Field: `section` (optional spot-check)

When reviewing sectioner output, mark whether `text_resp` / `text_qual` look correctly split: `ok` / `bad`. Used for κ on section quality, not for Q4 scores.

## Process

1. Run `python -m validation.sample_golden` to write the stratified sample under `AJT_DATA/processed/golden/` (IDs, title, auto family, period — no body text in git).
2. Each author fills `family_human` and `ai_bullet` in their own copy (`labels_<you>.csv`).
3. Run `python -m validation.kappa --a labels_a.csv --b labels_b.csv` and record κ in the PR / paper notes.
4. After discussion, write `labels_consensus.csv` locally; commit only aggregate κ numbers, not scraped bodies.
