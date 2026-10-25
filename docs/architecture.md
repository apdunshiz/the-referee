# Architecture

One Python toolchain (decision D32). The bot writes `content/` through a pull request; the renderer reads `content/` and writes `_site/`; GitHub Actions wires cron → bot → PR → CI → merge → Pages.

```
  GitHub repo (public), branch main
  ├ content/questions/*.md             ◄── human PRs (CODEOWNERS: maintainer)
  ├ content/claims/*.md (locked)       ◄── human PRs; CI lock check (version bump + history line)
  ├ content/claims/new/*.md (drafts)   ◄── bot PR   (no verdict, D28)
  ├ content/sightings/<fullname>.json  ◄── bot PR   {fullname, permalink, claim_id, match_confidence, matched_at}
  ├ content/site.json, status.json, schema/*.json (exported), evals/fixture.jsonl
  ├ referee/  reddit.py  mapper.py  content.py  gitops.py  run.py
  ├ site/     render.py  templates/  static/
  └ .github/workflows/  ingest.yml  ci.yml  pages.yml  stale.yml

  cron 10:00 + 16:00 UTC ─► ingest.yml ─► python -m referee.run prepare ─► Reddit API (OAuth) + Claude API
                                       ─► mint App token ─► python -m referee.run publish ─► PR (bot/<date>)
                                       ─► ci.yml (pytest, validate, schema check, render, lock check) ─► auto-merge
  on: push main ─► pages.yml ─► python site/render.py ─► upload-pages-artifact ─► deploy-pages ─► smoke test
  every 12 h    ─► stale.yml reads status.json.last_success; issue + banner after 36 h
```

## Daily run (referee/run.py)

```
  prepare:  preflight ─► fetch (7-day window, full comment trees, morechildren)
            ─► map (structured output over the closed claim-id enum; quote verified then discarded)
            ─► dedupe (second pass over this run's drafts) ─► recheck (last 30 days via /api/info)
            ─► validate ─► write sightings/drafts/status.json ─► commit on bot/<date>
  publish:  push ─► gh pr create ─► gh pr merge --auto --squash
  Nothing is written before mapping completes; a failure before `write` publishes nothing.
  12:00 slot: full run if 06:00 recorded a fetch failure; carried-only if degraded; no-op if it succeeded.
```

## Why these shapes

- Locked rulings plus a mapper (not a judge): the bot can only point at rulings, never change one. Drift is impossible by construction.
- No stored quotes: a sighting is ids and a link, so nothing personal lives in the repository and deletions propagate from Reddit through the daily recheck.
- Flat `content/sightings/` (D22): upgrade to monthly shards when the build exceeds 60 s or 10k files; the path builder carries a `gstack-shortcut(dec-SHARD)` marker.
- Python for the site (D32): the renderer reuses the PDF's data shapes and CSS; pydantic models are the single schema, exported to `schema/*.json` for editors.
