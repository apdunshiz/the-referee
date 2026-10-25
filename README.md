# The Referee

Arguments for and against God, graded with one public rubric and a confidence % per ruling, kept current from r/DebateAChristian by a daily bot that maps new comments onto locked rulings. The bot never rules; humans change rulings by pull request.

Status: v0.1 under review (content, site renderer, daily bot and workflows). The plan behind it is summarised in `docs/`.

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
- `content/evidence/<for|against>-NN.md`: one line of evidence for or against God. `strength` (0–10) weighs the best defensible version of the argument as evidence; `confidence` (%) is how sure the referee is of that weight. The home page sums each side's strengths, which is a reading aid, not a verdict.
- `content/worldviews/<id>.md`: one religion or non-religious stance, scored 0–10 with a confidence % on every criterion in `content/site.json` (`criteria`). The comparison page sorts by the summed score; the reasoning behind each number is on the worldview's page. These records change only by human PR, like rulings.
- `schema/*.json`: exported from the pydantic models in `referee/content.py`; CI fails when stale.

## Site

The site is static HTML rendered by Python; no Node toolchain.

```
.venv/bin/python site/render.py --out _site                      # local preview: open _site/index.html
.venv/bin/python site/render.py --out _site --base /the-referee/ # as served at https://apdunshiz.github.io/the-referee/
```

- `site/render.py`: loads `content/` and `status.json` through the models and writes one page per question and claim plus `/today/`, `/about/`, `/rubric/`, `/404.html` and a copy of `status.json`.
- `site/templates/*.html.j2`: Jinja2 templates with autoescaping on; no content field is ever marked safe.
- `site/static/tokens.css`: the visual system (navy and gold, text badges, segmented meters), ported from the October 2026 review PDF; `site/static/fonts/` holds the local Inter and Source Serif 4 files.
- `content/site.json`: the home-page scoreboard, the rubric legend and the historical-facts table (`SiteData` model).
- `tests/test_render.py`: page rendering, escaping, every Today state, drafts rule, base-path prefixing, and a timed render of the real content.

Correcting a ruling: edit the claim file, bump `version`, add a `history` line, open a PR.

## Bot

`referee/` is the daily job (Python only, decision D32/D33): `reddit.py` (official OAuth script app, read-only), `mapper.py` (one structured Claude call per unit; the bot never rules), `gitops.py` (branch, commit, PR, auto-merge through `gh`), `run.py` (the step runner), `config.py` (tunables, incl. `MATCH_THRESHOLD`).

Environment (repository secrets in Actions; never printed): `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` (the owning account must have 2FA off), `ANTHROPIC_API_KEY`, `GH_TOKEN` (minted by the workflow from the GitHub App). Repository variable `INGEST_ENABLED=false` pauses the job; it then writes `paused: true` to `status.json` and exits 0.

```
.venv/bin/python -m referee.run prepare --slot morning --dry-run   # fetch + map, write nothing, print the plan
.venv/bin/python -m referee.run prepare --slot morning             # ... and commit on bot/<date>-morning
.venv/bin/python -m referee.run publish                            # push, open the PR, enable auto-merge
.venv/bin/python -m referee.run prepare --slot noon                # full run after a failed morning, carried-only after a degraded one, no-op otherwise
.venv/bin/python -m referee.mapper eval evals/fixture.jsonl        # claim-level precision/recall per threshold (see evals/README.md)
```

The workflow runs `prepare`, mints a fresh App token, then runs `publish` with `if: always()`, so a failed run still publishes its `status.json` and the site shows the failure banner. Nothing under `content/` is written before mapping completes; a failure after the write step discards the content changes and commits `status.json` only. Steps: preflight → fetch (7-day window, full comment trees, `more` stubs expanded) → map → dedupe (second pass merges this run's new arguments with each other and with existing drafts) → recheck (last 30 days of sightings against `/api/info`; deleted sources are dropped) → write → validate → commit.
