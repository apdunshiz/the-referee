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
