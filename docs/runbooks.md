# Runbooks

Every alert is a GitHub issue labelled `ingest`, plus a banner on the Today page. Logs are in the Actions run; `status.json` holds the last 30 runs.

## 1. "Ingest failed <date>" with RedditAuthError

Cause: the script app's password grant failed. Reddit script apps cannot log in to an account with two-factor authentication on (decision D21: the bot reads as the maintainer's own account).
1. Check 2FA is still off on the account and the app still exists at reddit.com/prefs/apps.
2. If the password was changed, update the `REDDIT_PASSWORD` secret.
3. Run `ingest` by hand with `dry_run=true`; it should reach the mapping step.

## 2. "Bot PR stuck" / PrExists

Cause: an earlier `bot/<date>-<slot>` PR did not merge (a CI check failed or the ruleset blocked it).
1. Open the PR; read the failing check. A schema or lock failure means the bot produced a file the models reject: fix `referee/` and re-run, or close the PR.
2. If every check is green and it still did not merge, the App is missing from a ruleset's bypass list or "Allow auto-merge" is off in repository settings.
3. Close or merge the PR, then run `ingest` by hand.

## 3. "No successful run since <date>" (stale.yml)

Cause: the cron did not fire, or every run failed, for 36 hours.
1. Check https://www.githubstatus.com and the Actions tab. GitHub disables schedules on repositories with no activity for 60 days; the daily merges normally prevent that.
2. Run `ingest` by hand (`workflow_dispatch`, `dry_run=false`).
3. If `INGEST_ENABLED` is `false`, the watchdog is skipped on purpose (see runbook 5).

## 4. Someone asks for a comment to be removed

Nothing of theirs is stored: a sighting holds the Reddit id, a permalink, a claim id and a score (decision D27). If they delete the comment on Reddit, the next daily run's 30-day recheck drops the sighting. To remove it sooner, delete `content/sightings/<fullname>.json` in a PR.

## 5. Pause the bot

Set the repository variable `INGEST_ENABLED` to `false`. The next run exits cleanly with `paused: true` in `status.json` and the Today page shows "Updates paused by the maintainer". The watchdog ignores the paused state. Set it back to `true` to resume.

## 6. Claude budget hit every day

Cause: more units than the per-run budget (2M input / 200k output tokens) can map; carried units pile up.
1. Look at `runs[].carried` in `status.json`.
2. Either raise the budget constants in `referee/config.py` or raise the 200-character unit bar.

## 7. Rotate the Reddit password or the App key

Change it at the source, update the secret (`REDDIT_PASSWORD` or `APP_PRIVATE_KEY`), run `ingest` with `dry_run=true`.
