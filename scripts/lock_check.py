"""CI lock check for pull requests.

Bot PRs may touch only sightings, drafts and status.json. Human PRs may touch
anything, but a locked claim whose content changes needs version+1 and a new
history entry (decision D12, "the lock rule").

Usage: python scripts/lock_check.py --base <sha> --actor <login> [--bot-login <login>]

Only the content bot's own login (default ``the-referee[bot]``, or ``BOT_LOGIN`` in
the environment) takes the bot path; Dependabot and every other actor are humans.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import frontmatter  # noqa: E402

from referee.content import Claim, lock_check, locked_claim_bump_ok  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def claim_at(ref: str, path: str) -> Claim | None:
    try:
        text = git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None
    post = frontmatter.loads(text)
    data = dict(post.metadata)
    data["body"] = post.content.strip()
    return Claim.model_validate(data)


DEFAULT_BOT_LOGIN = "the-referee[bot]"


def classify_actor(login: str, bot_login: str = DEFAULT_BOT_LOGIN) -> str:
    return "bot" if login == bot_login else "human"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--actor", required=True)
    ap.add_argument("--bot-login", default=os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN))
    args = ap.parse_args(argv)
    # --no-renames: a locked claim renamed into claims/new/ must show as a change to the locked path.
    changed = [p for p in git("diff", "--no-renames", "--name-only", f"{args.base}...HEAD").splitlines() if p]
    actor = classify_actor(args.actor, args.bot_login)
    problems = lock_check(changed, actor)
    if actor == "human":
        for path in changed:
            if path.startswith("content/claims/") and path.endswith(".md") and "/new/" not in path:
                before = claim_at(args.base, path)
                after = claim_at("HEAD", path)
                if after is not None:
                    problems += locked_claim_bump_ok(before, after)
    for p in problems:
        print(f"::error::{p}")
    print(f"{len(changed)} changed files, actor={actor}, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
