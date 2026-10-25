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
