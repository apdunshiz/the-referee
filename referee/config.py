"""Tunables for the bot. Values that an eval or an operator sets live here."""

SUBREDDIT = "DebateAChristian"
THREAD_HOST = "https://www.reddit.com"

# Mapper
MODEL = "claude-sonnet-5-5"
# Placeholder until the claim-level eval (decision D31) records the derived value:
# `python -m referee.mapper eval evals/fixture.jsonl` prints precision/recall per
# threshold; pick the lowest threshold with precision >= 0.85 and recall >= 0.7
# and write it here with the baseline numbers in docs/eval-baseline.md.
MATCH_THRESHOLD = 0.85
BUDGET_INPUT_TOKENS = 2_000_000
BUDGET_OUTPUT_TOKENS = 200_000
MAPPER_MAX_TOKENS = 512
MAPPER_TIMEOUT_S = 60.0
MAPPER_BACKOFF_S = (2, 8, 30)

# Units
MIN_UNIT_CHARS = 200
MAX_UNIT_CHARS = 40_000
WINDOW_DAYS = 7
RECHECK_DAYS = 30
RECHECK_MAX_DROP_RATIO = 0.5  # an /api/info answer that would drop more than this share is treated as broken, not as mass deletion
RECHECK_RATIO_MIN_SAMPLE = 4  # the ratio rule needs a sample; one deleted comment out of one is just a deletion
DRAFT_PUBLISH_SIGHTINGS = 2  # decision D28: a draft shows on Today after two sightings

# Reddit
REDDIT_TIMEOUT_S = 30.0
REDDIT_BACKOFF_S = (5, 30, 120)
REDDIT_RATELIMIT_SLEEP_CAP_S = 600
USER_AGENT = "the-referee/0.1 by {username}"

# Runs
RUNS_KEPT = 30
DEGRADED_FAILURE_RATIO = 0.5
