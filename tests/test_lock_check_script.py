"""scripts/lock_check.py against a real tiny git repository."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "lock_check.py"

CLAIM = """---
id: q01-c01
question: q01
text: The universe had a beginning.
side: skeptic
verdict: OPEN
strength: 5
why: A beginning is a live position but not an established finding.
sources: []
confidence: 90
status: locked
version: {version}
history: {history}
---
"""


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def run_check(cwd, base, actor, env_extra=None, head_ref=None):
    import os

    env = {**os.environ, **(env_extra or {})}
    env.pop("HEAD_REF", None)
    args = [sys.executable, str(SCRIPT), "--base", base, "--actor", actor]
    if head_ref is not None:
        args += ["--head-ref", head_ref]
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "content" / "claims" / "new").mkdir(parents=True)
    (tmp_path / "content" / "sightings").mkdir(parents=True)
    (tmp_path / "content" / "claims" / "q01-c01.md").write_text(CLAIM.format(version=1, history="[]"), encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    git(tmp_path, "checkout", "-q", "-b", "pr")
    return tmp_path, base


def commit_all(cwd, msg):
    git(cwd, "add", "-A")
    git(cwd, "commit", "-q", "-m", msg)


def test_bot_may_touch_sightings_only(repo):
    cwd, base = repo
    (cwd / "content" / "sightings" / "t1_abc.json").write_text("{}", encoding="utf-8")
    commit_all(cwd, "sighting")
    rc, out = run_check(cwd, base, "the-referee[bot]", head_ref="bot/2026-10-24-morning")
    assert rc == 0 and "actor=bot" in out
    (cwd / "content" / "claims" / "q01-c01.md").write_text(CLAIM.format(version=2, history="[]"), encoding="utf-8")
    commit_all(cwd, "bot edits a ruling")
    rc, out = run_check(cwd, base, "the-referee[bot]", head_ref="bot/2026-10-24-morning")
    assert rc == 1 and "may not change content/claims/q01-c01.md" in out


def test_dependabot_is_a_human_actor(repo):
    cwd, base = repo
    (cwd / "requirements.txt").write_text("pydantic>=2.11\n", encoding="utf-8")
    commit_all(cwd, "bump")
    rc, out = run_check(cwd, base, "dependabot[bot]")
    assert rc == 0 and "actor=human" in out


def test_bot_login_comes_from_env(repo):
    cwd, base = repo
    (cwd / "content" / "claims" / "q01-c01.md").write_text(CLAIM.format(version=2, history="[]"), encoding="utf-8")
    commit_all(cwd, "edit")
    rc, _ = run_check(cwd, base, "custom-bot[bot]", {"BOT_LOGIN": "custom-bot[bot]"})
    assert rc == 1


def test_human_edit_needs_version_bump_and_history(repo):
    cwd, base = repo
    (cwd / "content" / "claims" / "q01-c01.md").write_text(CLAIM.format(version=1, history="[]").replace("live position", "respectable position"), encoding="utf-8")
    commit_all(cwd, "edit without bump")
    rc, out = run_check(cwd, base, "apdunshiz")
    assert rc == 1 and "version is 1, expected 2" in out
    hist = "\n- date: '2026-10-24'\n  version: 2\n  note: Clarified wording."
    (cwd / "content" / "claims" / "q01-c01.md").write_text(CLAIM.format(version=2, history=hist).replace("live position", "respectable position"), encoding="utf-8")
    commit_all(cwd, "edit with bump")
    rc, out = run_check(cwd, base, "apdunshiz")
    assert rc == 0, out


def test_rename_into_new_is_seen_as_locked_change(repo):
    cwd, base = repo
    git(cwd, "mv", "content/claims/q01-c01.md", "content/claims/new/q01-c01.md")
    commit_all(cwd, "sneaky rename")
    rc, out = run_check(cwd, base, "the-referee[bot]")
    assert rc == 1 and "content/claims/q01-c01.md" in out


def test_bot_branch_from_another_login_fails_closed(repo):
    cwd, base = repo
    (cwd / "content" / "sightings" / "t1_abc.json").write_text("{}", encoding="utf-8")
    commit_all(cwd, "sighting")
    # The App's real login differs from BOT_LOGIN: the PR must not get the human path.
    rc, out = run_check(cwd, base, "the-referee-app[bot]", head_ref="bot/2026-10-24-morning")
    assert rc == 1 and "is a bot branch but the PR author is" in out
    rc, out = run_check(cwd, base, "the-referee-app[bot]", {"BOT_LOGIN": "the-referee-app[bot]"}, head_ref="bot/2026-10-24-morning")
    assert rc == 0 and "actor=bot" in out


def test_bot_login_on_a_non_bot_branch_fails(repo):
    cwd, base = repo
    (cwd / "content" / "sightings" / "t1_abc.json").write_text("{}", encoding="utf-8")
    commit_all(cwd, "sighting")
    rc, out = run_check(cwd, base, "the-referee[bot]", head_ref="feature/x")
    assert rc == 1 and "is not a bot/ branch" in out
    rc, out = run_check(cwd, base, "apdunshiz", head_ref="feature/x")
    assert rc == 0


def test_bot_login_without_head_ref_fails_closed():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from lock_check import actor_branch_problems

    assert actor_branch_problems("the-referee[bot]", "", "the-referee[bot]")
    assert actor_branch_problems("apdunshiz", "", "the-referee[bot]") == []
