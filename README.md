# The Referee

Arguments for and against God, graded with one public rubric and a confidence % per ruling, kept current from r/DebateAChristian by a daily bot that maps new comments onto locked rulings. The bot never rules; humans change rulings by pull request.

Status: lane S1 (content models and drafted records). The site renderer, bot and workflows follow the plan in `docs/`.

## Run

```
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m referee.content validate          # every file under content/ and status.json
.venv/bin/python -m referee.content export-schema     # regenerate schema/*.json from the models
.venv/bin/python -m pytest -q
```

## Content

- `content/questions/qNN.md`: one file per debate question (title, confidence, short and long verdict).
- `content/claims/qNN-cNN.md`: one locked ruling per claim. The first claims under each question are the original post's own lines; the rest are commenter claims, paraphrased with no usernames (decision D15) and no stored quotes (D27).
- `content/claims/new/`: drafts the bot could not match; they carry no verdict (D28).
- `content/sightings/<fullname>.json`: id, permalink, claim id, match confidence and time; nothing else.
- `schema/*.json`: exported from the pydantic models in `referee/content.py`; CI fails when stale.

Correcting a ruling: edit the claim file, bump `version`, add a `history` line, open a PR.

## Bot

`referee/` is the daily job (Python only, decision D32/D33): `reddit.py` (official OAuth script app, read-only), `mapper.py` (one structured Claude call per unit; the bot never rules), `gitops.py` (branch, commit, PR, auto-merge through `gh`), `run.py` (the step runner), `config.py` (tunables, incl. `MATCH_THRESHOLD`).

Environment (repository secrets in Actions; never printed): `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` (the owning account must have 2FA off), `ANTHROPIC_API_KEY`, `GH_TOKEN` (minted by the workflow from the GitHub App). Repository variable `INGEST_ENABLED=false` pauses the job; it then writes `paused: true` to `status.json` and exits 0.

```
.venv/bin/python -m referee.run prepare --slot morning --dry-run   # fetch + map, write nothing, print the plan
.venv/bin/python -m referee.run prepare --slot morning             # ... and commit on bot/<date>
.venv/bin/python -m referee.run publish                            # push, open the PR, enable auto-merge
.venv/bin/python -m referee.run prepare --slot noon                # full run after a failed morning, carried-only after a degraded one, no-op otherwise
.venv/bin/python -m referee.mapper eval evals/fixture.jsonl        # claim-level precision/recall per threshold (see evals/README.md)
```

The workflow runs `prepare`, mints a fresh App token, then runs `publish` with `if: always()`, so a failed run still publishes its `status.json` and the site shows the failure banner. Nothing under `content/` is written before mapping completes; a failure after the write step discards the content changes and commits `status.json` only. Steps: preflight → fetch (7-day window, full comment trees, `more` stubs expanded) → map → dedupe (second pass merges this run's new arguments with each other and with existing drafts) → recheck (last 30 days of sightings against `/api/info`; deleted sources are dropped) → write → validate → commit.
