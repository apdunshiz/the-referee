"""CI lock check for pull requests.

Bot PRs may touch only sightings, drafts and status.json. Human PRs may touch
anything, but a locked claim whose content changes needs version+1 and a new
history entry (decision D12, "the lock rule").

Usage: python scripts/lock_check.py --base <sha> --actor <login> [--head-ref <branch>] [--bot-login <login>]

Only the content bot's own login (default ``the-referee[bot]``, or ``BOT_LOGIN`` in
the environment) takes the bot path; Dependabot and every other actor are humans.
A ``bot/`` branch from any other login fails, so a mismatched BOT_LOGIN cannot
quietly give the bot the human path.
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


def actor_branch_problems(login: str, head_ref: str, bot_login: str = DEFAULT_BOT_LOGIN) -> list[str]:
    """Fail closed: a bot/ branch must come from the bot login, and the bot login must use a bot/ branch.

    Otherwise a wrong BOT_LOGIN (or an App installed under another slug) would silently
    hand the bot's PRs the human path, which allows every file.
    """
    is_bot_branch = head_ref.startswith("bot/")
    is_bot_login = login == bot_login
    if is_bot_branch and not is_bot_login:
        return [f"branch {head_ref} is a bot branch but the PR author is {login!r}, not the bot login {bot_login!r}; set the BOT_LOGIN variable to the App's login or use another branch name"]
    if is_bot_login and head_ref and not is_bot_branch:
        return [f"PR author {login!r} is the bot login but the branch {head_ref!r} is not a bot/ branch"]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--actor", required=True)
    ap.add_argument("--head-ref", default=os.environ.get("HEAD_REF", ""), help="the PR head branch name")
    ap.add_argument("--bot-login", default=os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN))
    args = ap.parse_args(argv)
    # --no-renames: a locked claim renamed into claims/new/ must show as a change to the locked path.
    changed = [p for p in git("diff", "--no-renames", "--name-only", f"{args.base}...HEAD").splitlines() if p]
    actor = classify_actor(args.actor, args.bot_login)
    problems = actor_branch_problems(args.actor, args.head_ref, args.bot_login)
    problems += lock_check(changed, actor)
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
