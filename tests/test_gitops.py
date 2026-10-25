import pytest

from referee.gitops import GhAuthError, GhUnavailable, GitOps, Result


class FakeRunner:
    """Scripted by command prefix; records calls in order."""

    def __init__(self, rules=None):
        self.rules = rules or {}
        self.calls = []

    def __call__(self, args):
        self.calls.append(list(args))
        for prefix, result in self.rules.items():
            if tuple(args[: len(prefix)]) == prefix:
                return result() if callable(result) else result
        return Result(0, "")


def test_auth_status_errors_are_classified():
    g = GitOps(FakeRunner({("gh", "auth", "status"): Result(1, "", "You are not logged into any GitHub hosts")}))
    with pytest.raises(GhAuthError):
        g.preflight_auth()
    g2 = GitOps(FakeRunner({("gh", "auth", "status"): Result(1, "", "dial tcp: connection refused")}))
    with pytest.raises(GhUnavailable):
        g2.preflight_auth()


def test_open_bot_prs_filters_by_author_login_and_branch_prefix():
    rows = (
        '[{"number": 7, "headRefName": "bot/2026-10-24-morning", "author": {"login": "the-referee[bot]"}},'
        ' {"number": 8, "headRefName": "fix-typo", "author": {"login": "the-referee[bot]"}},'
        ' {"number": 9, "headRefName": "bot/2026-10-24-morning", "author": {"login": "someone-else"}}]'
    )
    g = GitOps(FakeRunner({("gh", "pr", "list"): Result(0, rows)}), bot_login="the-referee[bot]")
    assert g.open_bot_prs() == [(7, "bot/2026-10-24-morning")]  # a fork's bot/ branch must not stall the run
    call = g.run.calls[0]
    assert "--search" in call and "head:bot/" in call and "@me" not in call and "author" in call[call.index("--json") + 1]


def test_bot_login_defaults_from_env(monkeypatch):
    monkeypatch.setenv("BOT_LOGIN", "custom-app[bot]")
    assert GitOps(FakeRunner()).bot_login == "custom-app[bot]"
    monkeypatch.delenv("BOT_LOGIN")
    assert GitOps(FakeRunner()).bot_login == "the-referee[bot]"


def test_publish_order_push_then_create_then_automerge():
    r = FakeRunner({("gh", "pr", "create"): Result(0, "https://github.com/x/y/pull/9\n")})
    g = GitOps(r)
    url = g.push_and_open_pr("bot/2026-10-24", "Referee: 2026-10-24", "body")
    assert url == "https://github.com/x/y/pull/9"
    kinds = [tuple(c[:3]) for c in r.calls]
    assert kinds == [("git", "push", "-u"), ("gh", "pr", "create"), ("gh", "pr", "merge")]
    assert r.calls[2][3:6] == ["--auto", "--squash", "--delete-branch"]


def test_commit_all_reports_nothing_to_commit():
    r = FakeRunner({("git", "status"): Result(0, "")})
    assert GitOps(r).commit_all("msg") is False
    r2 = FakeRunner({("git", "status"): Result(0, " M status.json\n")})
    assert GitOps(r2).commit_all("msg") is True
    assert any(c[:2] == ["git", "-c"] and "commit" in c for c in r2.calls)


def test_branch_from_main_fetches_first():
    r = FakeRunner()
    GitOps(r).branch_from_main("bot/2026-10-24")
    assert r.calls == [["git", "fetch", "origin", "main"], ["git", "checkout", "-B", "bot/2026-10-24", "origin/main"]]


def test_has_unpushed_commits():
    assert GitOps(FakeRunner({("git", "rev-list"): Result(0, "2\n")})).has_unpushed_commits() is True
    assert GitOps(FakeRunner({("git", "rev-list"): Result(0, "0\n")})).has_unpushed_commits() is False
