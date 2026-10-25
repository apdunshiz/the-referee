"""Git and GitHub operations for the daily PR. All commands go through an injected runner.

The GitHub App token is minted by the workflow (actions/create-github-app-token) and
arrives as GH_TOKEN. This module never mints or logs tokens. The workflow calls
``run.py prepare`` (which commits locally) and then, after a fresh mint,
``run.py publish`` (which pushes and opens the PR).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


@dataclass
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str]], Result]


def subprocess_runner(cwd: Optional[str] = None) -> Runner:
    def run(args: Sequence[str]) -> Result:
        try:
            p = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, timeout=600)
        except FileNotFoundError as e:
            raise GhUnavailable(f"{args[0]} not found") from e
        except subprocess.TimeoutExpired as e:
            raise GhUnavailable(f"{args[0]} timed out") from e
        return Result(p.returncode, p.stdout, p.stderr)

    return run


class GitOpsError(Exception):
    pass


class GhAuthError(GitOpsError):
    pass


class GhUnavailable(GitOpsError):
    pass


class PrExists(GitOpsError):
    def __init__(self, number: int, branch: str):
        super().__init__(f"bot PR #{number} on {branch} is still open")
        self.number = number
        self.branch = branch


class GitOps:
    def __init__(self, run: Runner, author: str = "The Referee bot <referee-bot@users.noreply.github.com>"):
        self.run = run
        self.author = author

    def _gh(self, *args: str) -> Result:
        r = self.run(["gh", *args])
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").lower()
            if "auth" in err or "401" in err or "not logged" in err or "token" in err:
                raise GhAuthError(f"gh {args[0]}: {(r.stderr or r.stdout).strip()[:200]}")
            raise GhUnavailable(f"gh {args[0]}: {(r.stderr or r.stdout).strip()[:200]}")
        return r

    def _git(self, *args: str) -> Result:
        r = self.run(["git", *args])
        if r.returncode != 0:
            raise GhUnavailable(f"git {args[0]}: {(r.stderr or r.stdout).strip()[:200]}")
        return r

    def preflight_auth(self) -> None:
        self._gh("auth", "status")

    def open_bot_prs(self) -> list[tuple[int, str]]:
        # Only the bot's own PRs count; a fork PR on a bot/ branch must not stall the daily run.
        r = self._gh("pr", "list", "--state", "open", "--author", "@me", "--json", "number,headRefName", "--limit", "50")
        try:
            rows = json.loads(r.stdout or "[]")
        except ValueError as e:
            raise GhUnavailable("gh pr list returned non-JSON") from e
        return [(int(x["number"]), x["headRefName"]) for x in rows if str(x.get("headRefName", "")).startswith("bot/")]

    def comment_pr(self, number: int, body: str) -> None:
        self._gh("pr", "comment", str(number), "--body", body)

    def branch_from_main(self, branch: str) -> None:
        self._git("fetch", "origin", "main")
        self._git("checkout", "-B", branch, "origin/main")

    def commit_all(self, message: str) -> bool:
        self._git("add", "-A")
        status = self._git("status", "--porcelain")
        if not status.stdout.strip():
            return False
        self._git("-c", f"user.name={self.author.split(' <')[0]}", "-c", f"user.email={self.author.split('<')[1].rstrip('>')}", "commit", "-q", "-m", message)
        return True

    def push_and_open_pr(self, branch: str, title: str, body: str) -> str:
        self._git("push", "-u", "origin", branch)
        r = self._gh("pr", "create", "-B", "main", "-H", branch, "-t", title, "-b", body)
        url = (r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else branch
        self._gh("pr", "merge", "--auto", "--squash", "--delete-branch", url)
        return url

    def discard_content(self) -> None:
        """Throw away uncommitted changes under content/ (used when a run fails after the write step)."""
        self._git("checkout", "--", "content/")
        self._git("clean", "-fdq", "content/")

    def has_unpushed_commits(self) -> bool:
        r = self._git("rev-list", "--count", "origin/main..HEAD")
        return int((r.stdout or "0").strip() or 0) > 0
