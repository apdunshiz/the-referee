# Mapper eval fixture

`fixture.jsonl` is the hand-labelled set the claim-level eval runs on (decision D31). One JSON object per line:

```json
{"text": "<the argument in your own words, >= 200 chars, no usernames>", "claim_id": "q09-c07"}
{"text": "<a comment that makes no listed claim>", "claim_id": null}
```

- `claim_id` is the id of the one locked claim the text makes (`content/claims/<id>.md`), or `null` when it makes none. If a text makes two listed claims, pick the main one; the eval scores exact matches.
- Start with the 48 top-level comments of the Oct 21 thread (`data/tree.json` in the review scratch dir), then add replies until about 100 lines. Aim for at least 30 `null` rows so precision is measured.
- The fixture is for evaluation only and never ships to the site, but it lives in this public repository: write each row as a paraphrase in your own words, never verbatim Reddit text, and never a username (decisions D15 and D27). Keep the paraphrase close enough in length and content that the mapper sees the same argument.

Run:

```
ANTHROPIC_API_KEY=... .venv/bin/python -m referee.mapper eval evals/fixture.jsonl
```

It prints precision and recall per threshold from 0.50 to 0.95 and the tokens spent. Pick the lowest threshold with precision >= 0.85 and recall >= 0.70, write it to `MATCH_THRESHOLD` in `referee/config.py`, and record the table in `docs/eval-baseline.md`. Re-run on any prompt or model change.
