# Data sources: what works and what we found

Endpoints and coverage checked on 2026-11-13. All settings live in [`config.yaml`](../config.yaml); the code is in [`pipeline/`](../pipeline).

**One rule for every source:** use only public endpoints, with the project's own User-Agent, one request at a time per site. If a site has a bot check or needs a session token, it is out of scope. Never use browser user-agents, copied cookies, CSRF tokens or headless browsers.

## 1. Full job boards (`make boards`)

Every open role, saved as the raw API response in `raw/boards/<date>/`. About 30 MB per pull (OpenAI alone is 14 MB).

| Group | Companies (board name) |
| --- | --- |
| AI-native | Anthropic, Scale AI (`scaleai`), Glean (`gleanwork`) on Greenhouse; OpenAI, Cohere, Sierra, Harvey on Ashby |
| Data / software | Palantir (Lever), Databricks (Greenhouse), Snowflake (Ashby) |
| Consulting | Thoughtworks (Greenhouse) |
| VC / accelerator, own roles | a16z (Greenhouse, ~23 roles), Y Combinator (Ashby `ycombinator`, ~9 roles) |

Endpoints:

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<name>/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/<name>?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/<name>`

Not found under the obvious names: Mistral AI, Sequoia, General Catalyst, Accel. The `lightspeed` Ashby board is a robotics company, not the VC.

**Live boards only show today's roles.** Every week we don't collect is lost: see the weekly pull in the [README](../README.md#weekly-pull).

## 2. Big employers by keyword search (`make employers`)

The Magnificent 7, consulting firms, large tech and telcos run their own careers sites. Those with a public search API are searched for every term in `search_terms` (English plus three Spanish terms). Full text is fetched only for titles in a target family; other titles are kept for title counts.

| Group | Covered (system) | Not reachable |
| --- | --- | --- |
| Magnificent 7 | Amazon (amazon.jobs), Microsoft (careers API), Nvidia (Workday) | Apple, Alphabet/Google, Meta, Tesla |
| Consulting / IT services | Accenture, PwC (Workday), Capgemini (own API), Thoughtworks (board) | Deloitte, KPMG, EY, McKinsey, BCG, Bain, IBM |
| Large tech | Salesforce, Cisco (Workday), ServiceNow (SmartRecruiters) | SAP, Oracle |
| Telco | AT&T, T-Mobile (Workday), Telefónica, Vodafone (SuccessFactors RSS), Telefónica Tech (SmartRecruiters) | Orange, Deutsche Telekom (not checked) |
| VC / accelerator | a16z, Y Combinator (own roles, on the boards) | Portfolio job boards (e.g. jobs.a16z.com): possible add-on |

**The unreachable firms are still in the study** through the H-1B LCA filings (Q9), where Apple, Google, Meta and Tesla each file thousands of cases with job titles every year, and through the Kaggle LinkedIn sets.

Things to know:

- **Microsoft rate-limits hard**, especially from GitHub's servers. It is limited to one call every 10 seconds and 50 listings per term. When an employer stops on repeated HTTP 429, what it collected is saved as `<name>.partial.jsonl.gz` with `<name>.progress.json`, and the next run on the same day resumes from the last finished search term. The weekly workflow makes a second pass 15 minutes later; locally, re-run `make employers`.
- **Some Workday listings have no job link** (seen at Accenture and T-Mobile); they are skipped.
- **Keyword searches are samples.** Do not compare raw counts between boards and searches; compare shares within a company.
- **Workday list pages hide locations** ("2 Locations"); the location comes from the posting details.
- **SuccessFactors RSS** returns about 20 newest matches per search, with no paging, and its keyword match is loose: for Telefónica, "forward deployed" returns network-security and sales roles. Expect few target-family postings from Telefónica and Vodafone; the family patterns, not the search term, decide what counts.
- **Runtime:** about an hour for the full term list, mostly Microsoft.

**Early signal:** FDE is not just an AI-lab title. In the test run, Amazon ("Forward Deployed Engineer, AWS Forward Deployed Engineering"), Microsoft, Nvidia ("Forward Deployed Architect"), Accenture, Capgemini, PwC ("Deals AI Forward Deployed Engineer"), Salesforce, Cisco, ServiceNow and AT&T all posted it. Q1 can compare FDE against SA within the same employer.

**Spanish postings:** Telefónica posts mostly in Spanish. Spanish titles are recognised and flagged `spain`, but non-English text is out of scope for the v1 text analyses: use it for title counts and a Spain comparison only. The test run found Accenture FDE roles in Madrid, a Salesforce FDE in Barcelona and Capgemini's "Arquitecto/a de Soluciones AI".

## 3. Wayback Machine coverage test (`make wayback`)

The week-1 go/no-go gate. For each prefix in `config.yaml`: count archived posting URLs per period, then fetch a sample of snapshots and check each has a title and a responsibilities section.

- `jobs.lever.co/palantir/` has no snapshots before December 2020.
- **The 2010–16 Palantir postings that Q8 needs are archived** at `palantir.com/careers/OpenPosDetail?id=…` and `PositionDetail?id=…`, about 370 posting URLs. A 2013 page has full text with a Responsibilities section about scoping customer deployments. The page `<title>` is generic ("Open Positions | Palantir"), so take the job title from the page heading.
- Scale AI's Lever board has ~50 posting URLs from before December 2022 (P0); all sampled pages were usable.
- Pass mark (suggested, not agreed): 30 usable postings per family per period.

**Archived postings with text (`make archive`).** The coverage test only checks a sample; `make archive`
saves title and text for archived postings of the companies in `wayback.collect` (Palantir, Databricks,
OpenAI, Anthropic, Scale AI), at most 300 per address and period, one earliest snapshot per job. Where the
URL carries the title (Databricks: `.../partner-solutions-architect-83478800`), only target-family
postings are fetched. Databricks' own careers site has ~7,500 archived posting URLs from 2020 to 2026,
which gives a same-company Solutions Architect history next to its new FDE roles. Saved as append-only
JSON lines in `raw/wayback/`, so an interrupted run keeps everything up to the last line.

Raw snapshots are fetched from `https://web.archive.org/web/<timestamp>id_/<url>` at most once a second and cached in `cache/wayback/` so an interrupted run resumes. Failed downloads are not kept in the cache, so a re-run retries them.

**The Archive refuses connections after heavy use** (seen twice on 2026-11-13). Run the gate once, not repeatedly, and if it stalls, wait an hour and re-run: finished work is cached.

First partial results (2026-11-13), estimated usable postings: Palantir Lever board ~450 and old palantir.com careers ~340, both before Dec 2022; OpenAI Greenhouse ~130 before Dec 2022 and ~290 for Dec 2022–2024; OpenAI Lever ~60 before Dec 2022. Palantir Lever after 2022, OpenAI Ashby, Anthropic, Scale AI and Google Cloud still to check.

## 4. HN "Who is Hiring" (`make hn`)

BigQuery `bigquery-public-data.hacker_news.full` when `GCP_PROJECT` is set (the run prints the GB scanned first; free tier 1,000 GB a month), otherwise the [Hugging Face copy](https://huggingface.co/datasets/brusic/hacker-news-who-is-hiring-posts). Check the month-by-month counts from April 2011: missing months mean the thread wasn't posted by `whoishiring`.

The Hugging Face copy stores one row per monthly thread with its comments nested; the loader unpacks it to one row per comment (same columns as the BigQuery query) and drops usernames. Checked 2026-11-13: 184 "Who is hiring" threads, April 2011 to September 2026, missing July 2011, April 2015 and May 2015.

## 5. Kaggle LinkedIn sets (`make kaggle`)

`arshkon/linkedin-job-postings` and `asaniczka/1-3m-linkedin-jobs-and-skills-2024`, converted to Parquet with only the columns we use. Scraped data: publish aggregates only.

## 6. Benchmarks to cite (not data)

- **nothiring, [Tech job market in Spain, Q3 2026](https://nothiring.me/blog/tech-job-market-spain)**: a recruiting agency's sample of 19,526 tech jobs in Spain, July–September 2026. It counts 75 FDE jobs in Spain (61% describe direct client work), and finds IT services and consulting post 42% of tech jobs and 46% of AI Engineer jobs. Its method differs from ours, so compare orders of magnitude only.
- **Indeed Hiring Lab AI Tracker** for the opening macro line (CC BY 4.0).
