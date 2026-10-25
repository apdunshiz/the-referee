import json
from datetime import datetime, timezone

import pytest

from referee import content
from referee.content import Draft, RunRecord, Sighting, Status
from referee.mapper import BudgetExhausted, DraftCandidate, MapOutcome, MapperTimeout
from referee.reddit import RedditGone, Unit
from referee.run import Context, RunFailed, prepare, publish, slugify

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
TS = NOW.timestamp()


def post(i, created=TS - 100):
    return {"name": f"t3_p{i}", "id": f"p{i}", "title": "Title", "selftext": "s" * 250, "created_utc": created, "permalink": f"/r/DebateAChristian/comments/p{i}/t/"}


def comment(i, created=TS - 50):
    return {"name": f"t1_c{i}", "id": f"c{i}", "body": "b" * 250, "author": "a", "created_utc": created, "link_id": "t3_p1", "permalink": f"/r/DebateAChristian/comments/p1/t/c{i}/"}


class FakeReddit:
    def __init__(self, posts=None, comments=None, present=None):
        self.posts = posts if posts is not None else [post(1)]
        self.comments = comments if comments is not None else [comment(1), comment(2), comment(3), comment(4)]
        self.present = present or {}
        self.calls = []

    def get_token(self):
        self.calls.append("token")
        return "t"

    def fetch_window(self, days):
        self.calls.append("window")
        return self.posts

    def fetch_comments(self, post_id):
        self.calls.append(("comments", post_id))
        if post_id == "gone":
            raise RedditGone("404")
        return self.comments

    def info(self, fullnames):
        self.calls.append(("info", sorted(fullnames)))
        return {f: self.present.get(f, True) for f in fullnames}


def sighting_for(u: Unit, cid="q01-c01"):
    return Sighting(fullname=u.fullname, permalink=u.permalink, claim_id=cid, match_confidence=0.9, matched_at="2026-10-24T10:00:00Z")


class FakeMapper:
    """outcomes: fullname -> MapOutcome | Exception | 'match' | 'new'."""

    def __init__(self, outcomes=None, root=None):
        self.outcomes = outcomes or {}
        self.root = root
        self.seen = []
        self.used_in = 10
        self.used_out = 2

    def map_unit(self, u):
        self.seen.append(u.fullname)
        if self.root is not None:
            assert not list((self.root / "content" / "sightings").glob("*.json")), "a sighting was written before mapping completed"
        o = self.outcomes.get(u.fullname, "match")
        if isinstance(o, Exception):
            raise o
        if o == "match":
            return MapOutcome(outcome="matched", sighting=sighting_for(u), claim_id="q01-c01", match_confidence=0.9)
        if o == "new":
            return MapOutcome(outcome="new_argument", draft_text=f"A new argument from {u.fullname}.")
        return o

    def dedupe_pass(self, candidates, existing):
        return candidates, {}


class FakeGitOps:
    def __init__(self, open_prs=None):
        self.calls = []
        self.open_prs = open_prs or []

    def preflight_auth(self):
        self.calls.append("auth")

    def open_bot_prs(self):
        return self.open_prs

    def comment_pr(self, n, body):
        self.calls.append(("comment", n))

    def branch_from_main(self, b):
        self.calls.append(("branch", b))

    def commit_all(self, msg):
        self.calls.append(("commit", msg))
        return True

    def discard_content(self):
        self.calls.append("discard")

    def has_unpushed_commits(self):
        return True

    def push_and_open_pr(self, branch, title, body):
        self.calls.append(("publish", branch, title))
        return "https://github.com/x/y/pull/1"


def ctx(root, reddit=None, mapper=None, gitops=None, env=None, slot="morning", **kw):
    logs = []
    c = Context(root=root, slot=slot, reddit=reddit or FakeReddit(), mapper=mapper or FakeMapper(), gitops=gitops or FakeGitOps(), env=env or {}, now=lambda: NOW, log_out=logs.append, **kw)
    c._logs = logs
    return c


def test_happy_run_writes_after_mapping_and_commits(content_root):
    m = FakeMapper({"t1_c2": "new", "t1_c3": MapOutcome(outcome="refused")}, root=content_root)
    c = ctx(content_root, mapper=m)
    assert prepare(c) == 0
    sightings = content.load_sightings(content_root)
    assert sorted(s.fullname for s in sightings) == ["t1_c1", "t1_c4", "t3_p1"]
    drafts = content.load_drafts(content_root)
    assert len(drafts) == 1 and drafts[0].sightings_count == 1 and drafts[0].first_seen == "2026-10-24"
    st = content.load_status(content_root)
    assert st.runs[-1].outcome == "success" and st.runs[-1].matched == 3 and st.runs[-1].model_refused == 1 and st.runs[-1].drafted == 1
    assert st.watermark == "2026-10-24T09:59:10Z" and st.errors == [] and st.degraded is False
    assert c.gitops.calls[:2] == [("branch", "bot/2026-10-24-morning"), "auth"] and c.gitops.calls[-1][0] == "commit"
    assert content.validate_tree(content_root) == []
    # log lines never carry text
    for line in c._logs:
        rec = json.loads(line)
        assert "text" not in rec and "quote" not in rec and rec["run_id"]


def test_all_units_fail_writes_nothing_but_status(content_root):
    m = FakeMapper({f: MapperTimeout("t") for f in ("t3_p1", "t1_c1", "t1_c2", "t1_c3", "t1_c4")})
    c = ctx(content_root, mapper=m)
    with pytest.raises(RunFailed):
        prepare(c)
    assert content.load_sightings(content_root) == []
    st = content.load_status(content_root)
    assert st.runs[-1].outcome == "failed" and st.errors[0].startswith("RunFailed@map")
    assert ("commit", "Referee: 2026-10-24 morning failed at map") in c.gitops.calls


def test_half_failures_is_degraded_and_publishes_partial(content_root):
    m = FakeMapper({"t1_c1": MapperTimeout("t"), "t1_c2": MapperTimeout("t"), "t1_c3": MapperTimeout("t")})
    c = ctx(content_root, mapper=m)
    assert prepare(c) == 0
    st = content.load_status(content_root)
    assert st.degraded is True and st.runs[-1].outcome == "degraded"
    assert sorted(st.carried) == ["t1_c1", "t1_c2", "t1_c3"]
    assert sorted(s.fullname for s in content.load_sightings(content_root)) == ["t1_c4", "t3_p1"]


def test_budget_exhausted_carries_the_rest(content_root):
    m = FakeMapper({"t1_c2": BudgetExhausted("spent")})
    c = ctx(content_root, mapper=m)
    assert prepare(c) == 0
    st = content.load_status(content_root)
    assert sorted(st.carried) == ["t1_c2", "t1_c3", "t1_c4"] and st.runs[-1].outcome == "success"
    assert m.seen == ["t3_p1", "t1_c1", "t1_c2"]


def test_paused_writes_status_and_exits_zero(content_root):
    c = ctx(content_root, env={"INGEST_ENABLED": "false"})
    assert prepare(c) == 0
    st = content.load_status(content_root)
    assert st.paused is True and st.runs[-1].outcome == "paused"
    assert "window" not in c.reddit.calls and ("branch", "bot/2026-10-24-morning") in c.gitops.calls


def test_open_bot_pr_skips_run(content_root):
    c = ctx(content_root, gitops=FakeGitOps(open_prs=[(7, "bot/2026-10-23")]))
    assert prepare(c) == 0
    assert ("comment", 7) in c.gitops.calls and "window" not in c.reddit.calls


def seed_status(root, outcome, carried=()):
    st = Status(runs=[RunRecord(run_id="m1", started_at="2026-10-24T06:00:00Z", outcome=outcome)], carried=list(carried), watermark="2026-10-24T05:00:00Z")
    content.save_status(root, st)


def test_noon_after_success_is_noop(content_root):
    seed_status(content_root, "success")
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert c.reddit.calls == []
    # the no-op is recorded (and committed) so About and the next noon check can see it
    assert c.gitops.calls == [("branch", "bot/2026-10-24-noon"), ("commit", "Referee: 2026-10-24 noon no-op")]
    assert content.load_status(content_root).runs[-1].outcome == "noop"


def test_noon_ignores_yesterdays_run(content_root):
    st = Status(runs=[RunRecord(run_id="y", started_at="2026-10-23T06:00:00Z", outcome="success")], watermark="2026-10-23T05:00:00Z")
    content.save_status(content_root, st)
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert "window" in c.reddit.calls and len(content.load_sightings(content_root)) == 5


def test_skipped_run_is_recorded(content_root):
    c = ctx(content_root, gitops=FakeGitOps(open_prs=[(7, "bot/2026-10-23")]))
    assert prepare(c) == 0
    st = content.load_status(content_root)
    assert st.runs[-1].outcome == "skipped"
    assert any(isinstance(x, tuple) and x[0] == "commit" and "skipped" in x[1] for x in c.gitops.calls)


def test_preflight_failure_commits_on_bot_branch_never_main(content_root):
    from referee.reddit import RedditAuthError

    class BadReddit(FakeReddit):
        def get_token(self):
            raise RedditAuthError("invalid_grant")

    c = ctx(content_root, reddit=BadReddit())
    with pytest.raises(RedditAuthError):
        prepare(c)
    calls = c.gitops.calls
    assert calls[0] == ("branch", "bot/2026-10-24-morning"), "the bot branch must exist before anything can fail"
    assert ("commit", "Referee: 2026-10-24 morning failed at preflight") in calls
    st = content.load_status(content_root)
    assert st.runs[-1].outcome == "failed" and st.errors == ["RedditAuthError@preflight"]


def test_branch_failure_never_commits(content_root):
    class NoBranch(FakeGitOps):
        def branch_from_main(self, b):
            raise RuntimeError("git fetch failed")

    c = ctx(content_root, gitops=NoBranch())
    with pytest.raises(RuntimeError):
        prepare(c)
    assert not any(isinstance(x, tuple) and x[0] == "commit" for x in c.gitops.calls)


def test_error_field_carries_no_message_text(content_root):
    m = FakeMapper({f: MapperTimeout("the comment said: something private") for f in ("t3_p1", "t1_c1", "t1_c2", "t1_c3", "t1_c4")})
    c = ctx(content_root, mapper=m)
    with pytest.raises(RunFailed):
        prepare(c)
    st = content.load_status(content_root)
    assert st.errors == ["RunFailed@map"]
    assert "private" not in json.dumps(st.model_dump(mode="json"))


def test_validate_failure_restores_status_and_records_once(content_root, monkeypatch):
    content.save_status(content_root, Status(watermark="2026-10-20T00:00:00Z", last_success="2026-10-20T06:00:00Z", carried=["t1_old"]))
    from referee import run as run_mod

    monkeypatch.setattr(run_mod.content, "validate_tree", lambda root: ["content/claims/q01-c01.md: broken"])
    c = ctx(content_root)
    with pytest.raises(run_mod.ContentInvalid):
        prepare(c)
    st = content.load_status(content_root)
    assert st.watermark == "2026-10-20T00:00:00Z" and st.last_success == "2026-10-20T06:00:00Z" and st.carried == ["t1_old"]
    assert [r.run_id for r in st.runs].count(c.record.run_id) == 1 and st.runs[-1].outcome == "failed"
    assert st.errors == ["ContentInvalid@validate"] and "discard" in c.gitops.calls


def test_watermark_never_decreases(content_root):
    # A degraded morning left t1_c1 carried; the noon run processes only that old unit.
    content.save_status(content_root, Status(runs=[RunRecord(run_id="m", started_at="2026-10-24T06:00:00Z", outcome="degraded")], carried=["t1_c1"], watermark="2026-10-24T09:59:50Z"))
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert c.mapper.seen == ["t1_c1"]
    assert content.load_status(content_root).watermark == "2026-10-24T09:59:50Z"


def test_reprocessed_unit_does_not_inflate_draft_count(content_root):
    link = "https://www.reddit.com/r/DebateAChristian/comments/p1/t/c1/"
    content.save_draft(content_root, Draft(slug="hell-unjust-abc123", text="Hell is unjust punishment for finite sins.", first_seen="2026-10-20", sightings_count=1, links=[link]))

    class M(FakeMapper):
        def dedupe_pass(self, candidates, existing):
            return [], {"hell-unjust-abc123": [u for cnd in candidates for u in cnd.units]}

    c = ctx(content_root, mapper=M({"t1_c1": "new"}))
    assert prepare(c) == 0
    [d] = content.load_drafts(content_root)
    assert d.sightings_count == 1 and d.links == [link]


def test_sdk_api_error_per_unit_is_carried(content_root):
    import anthropic
    try:
        import httpx2 as httpx  # the SDK vendors httpx under this name
    except ImportError:  # pragma: no cover
        import httpx

    err = anthropic.APIConnectionError(message="boom", request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    c = ctx(content_root, mapper=FakeMapper({"t1_c2": err}))
    assert prepare(c) == 0
    st = content.load_status(content_root)
    assert st.carried == ["t1_c2"] and st.runs[-1].outcome == "success"


def test_publish_cli_accepts_workflow_argv(content_root, monkeypatch):
    from referee import run as run_mod

    g = FakeGitOps()
    monkeypatch.setattr(run_mod, "_gitops_factory", lambda root: g)
    content.save_status(content_root, Status(runs=[RunRecord(run_id="r", started_at="2026-10-24T10:00:00Z", outcome="success")]))
    assert run_mod.main(["publish", "--slot", "morning", "--root", str(content_root), "--date", "2026-10-24"]) == 0
    assert run_mod.main(["publish", "--slot", "noon", "--root", str(content_root), "--date", "2026-10-24"]) == 0
    assert [x[0] for x in g.calls] == ["publish", "publish"]


def test_noon_after_failure_is_full_run(content_root):
    seed_status(content_root, "failed")
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert "window" in c.reddit.calls and len(content.load_sightings(content_root)) == 5


def test_noon_after_degraded_processes_carried_only(content_root):
    seed_status(content_root, "degraded", carried=["t1_c2"])
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert c.mapper.seen == ["t1_c2"]
    assert [s.fullname for s in content.load_sightings(content_root)] == ["t1_c2"]


def test_watermark_and_existing_sightings_skip_units(content_root):
    content.save_sighting(content_root, Sighting(fullname="t1_c1", permalink="https://www.reddit.com/r/DebateAChristian/comments/p1/t/c1/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-01T10:00:00Z"))
    content.save_status(content_root, Status(watermark="2026-10-24T09:59:20Z"))  # TS-40; comments are TS-50, post TS-100
    reddit = FakeReddit(posts=[post(1)], comments=[comment(1), comment(2, created=TS - 10)])
    c = ctx(content_root, reddit=reddit, mapper=FakeMapper())
    assert prepare(c) == 0
    assert c.mapper.seen == ["t1_c2"]


def test_recheck_drops_deleted_sources(content_root):
    content.save_sighting(content_root, Sighting(fullname="t1_old", permalink="https://www.reddit.com/r/DebateAChristian/comments/p0/t/old/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-20T10:00:00Z"))
    content.save_sighting(content_root, Sighting(fullname="t1_ancient", permalink="https://www.reddit.com/r/DebateAChristian/comments/p0/t/anc/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-08-01T10:00:00Z"))
    reddit = FakeReddit(posts=[], comments=[], present={"t1_old": False})
    c = ctx(content_root, reddit=reddit, mapper=FakeMapper())
    assert prepare(c) == 0
    names = sorted(s.fullname for s in content.load_sightings(content_root))
    assert names == ["t1_ancient"]  # only the last 30 days are rechecked
    assert ("info", ["t1_old"]) in reddit.calls
    assert content.load_status(content_root).runs[-1].recheck_dropped == 1


def test_dry_run_writes_nothing(content_root):
    c = ctx(content_root, dry_run=True)
    assert prepare(c) == 0
    assert content.load_sightings(content_root) == [] and not (content_root / "status.json").exists()
    assert not any(call[0] == "commit" for call in c.gitops.calls if isinstance(call, tuple))


def test_existing_draft_gets_more_sightings(content_root):
    content.save_draft(content_root, Draft(slug="hell-unjust-abc123", text="Hell is unjust punishment for finite sins.", first_seen="2026-10-20", sightings_count=1, links=["https://www.reddit.com/r/DebateAChristian/comments/p0/t/a/"]))

    class M(FakeMapper):
        def dedupe_pass(self, candidates, existing):
            assert existing == [("hell-unjust-abc123", "Hell is unjust punishment for finite sins.")]
            return [], {"hell-unjust-abc123": [u for cnd in candidates for u in cnd.units]}

    c = ctx(content_root, mapper=M({"t1_c1": "new", "t1_c2": "new"}))
    assert prepare(c) == 0
    [d] = content.load_drafts(content_root)
    assert d.sightings_count == 3 and len(d.links) == 3


def test_publish_opens_pr_with_summary(content_root):
    content.save_status(content_root, Status(runs=[RunRecord(run_id="r", started_at="2026-10-24T10:00:00Z", outcome="success", matched=3, drafted=1)]))
    g = FakeGitOps()
    assert publish(content_root, g, "2026-10-24", log_out=lambda s: None) == 0
    assert g.calls == [("publish", "bot/2026-10-24-morning", "Referee: 2026-10-24 (success)")]


def test_slugify_is_stable_and_short():
    s = slugify("Bayesian priors make the resurrection a wash, whatever the evidence says about it.")
    assert s.startswith("bayesian-priors-make-the-resurrection-a-wash-whatever-") and len(s) <= 67
    assert slugify("!!!") .startswith("argument-")


def test_each_slot_has_its_own_branch_and_publish_matches(content_root):
    seed_status(content_root, "failed")
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert c.gitops.calls[0] == ("branch", "bot/2026-10-24-noon")
    g = FakeGitOps()
    assert publish(content_root, g, "2026-10-24", log_out=lambda s: None, slot="noon") == 0
    assert g.calls[0][1] == "bot/2026-10-24-noon"


def test_commit_failure_restores_status_and_records_once(content_root):
    content.save_status(content_root, Status(watermark="2026-10-20T00:00:00Z", last_success="2026-10-20T06:00:00Z"))

    class FlakyGit(FakeGitOps):
        def __init__(self):
            super().__init__()
            self.failed_once = False

        def commit_all(self, msg):
            if not self.failed_once and "failed at" not in msg:
                self.failed_once = True
                raise RuntimeError("index.lock exists")
            return super().commit_all(msg)

    c = ctx(content_root, gitops=FlakyGit())
    with pytest.raises(RuntimeError):
        prepare(c)
    st = content.load_status(content_root)
    assert st.watermark == "2026-10-20T00:00:00Z" and st.last_success == "2026-10-20T06:00:00Z"
    assert [r.run_id for r in st.runs].count(c.record.run_id) == 1 and st.runs[-1].outcome == "failed"
    assert st.errors == ["RuntimeError@commit"] and "discard" in c.gitops.calls


def test_noon_after_skipped_morning_is_full_run(content_root):
    seed_status(content_root, "skipped")
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert "window" in c.reddit.calls and len(content.load_sightings(content_root)) == 5


def test_noon_after_paused_morning_stays_noop(content_root):
    seed_status(content_root, "paused")
    c = ctx(content_root, slot="noon")
    assert prepare(c) == 0
    assert c.reddit.calls == [] and content.load_status(content_root).runs[-1].outcome == "noop"


def test_twenty_first_link_is_still_deduplicated(content_root):
    links = [f"https://www.reddit.com/r/DebateAChristian/comments/p1/t/x{i}/" for i in range(20)]
    content.save_draft(content_root, Draft(slug="hell-unjust-abc123", text="Hell is unjust punishment for finite sins.", first_seen="2026-10-20", sightings_count=20, links=links))
    reddit = FakeReddit(posts=[post(1)], comments=[comment(1)])

    class M(FakeMapper):
        def dedupe_pass(self, candidates, existing):
            return [], {"hell-unjust-abc123": [u for cnd in candidates for u in cnd.units]}

    # first pass: the 21st link is counted once
    c = ctx(content_root, reddit=reddit, mapper=M({"t1_c1": "new", "t3_p1": "new"}))
    assert prepare(c) == 0
    [d] = content.load_drafts(content_root)
    assert d.sightings_count == 22 and len(d.links) == 22
    # second pass over the same comment: nothing changes
    content.save_status(content_root, Status())
    c2 = ctx(content_root, reddit=reddit, mapper=M({"t1_c1": "new", "t3_p1": "new"}))
    assert prepare(c2) == 0
    [d2] = content.load_drafts(content_root)
    assert d2.sightings_count == 22 and len(d2.links) == 22


def _recent_sightings(root, n):
    for i in range(n):
        content.save_sighting(root, Sighting(fullname=f"t1_r{i}", permalink=f"https://www.reddit.com/r/DebateAChristian/comments/p0/t/r{i}/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-20T10:00:00Z"))


def test_recheck_skipped_when_answer_is_short(content_root):
    _recent_sightings(content_root, 4)

    class Short(FakeReddit):
        def info(self, fullnames):
            return {}  # an empty 200 from /api/info

    c = ctx(content_root, reddit=Short(posts=[], comments=[]))
    assert prepare(c) == 0
    assert len(content.load_sightings(content_root)) == 4
    rec = content.load_status(content_root).runs[-1]
    assert rec.recheck_skipped == 1 and rec.recheck_dropped == 0


def test_recheck_drops_every_explicit_deletion_even_when_many(content_root):
    _recent_sightings(content_root, 4)
    reddit = FakeReddit(posts=[], comments=[], present={"t1_r0": False, "t1_r1": False, "t1_r2": False})
    c = ctx(content_root, reddit=reddit)
    assert prepare(c) == 0
    assert len(content.load_sightings(content_root)) == 1  # a mod clearing a thread is a real deletion
    rec = content.load_status(content_root).runs[-1]
    assert rec.recheck_dropped == 3 and rec.recheck_skipped == 0


def test_recheck_partial_answer_drops_only_what_was_answered(content_root):
    _recent_sightings(content_root, 4)

    class Partial(FakeReddit):
        def info(self, fullnames):
            return {"t1_r0": False, "t1_r1": True}  # two names never answered

    c = ctx(content_root, reddit=Partial(posts=[], comments=[]))
    assert prepare(c) == 0
    assert len(content.load_sightings(content_root)) == 3
    rec = content.load_status(content_root).runs[-1]
    assert rec.recheck_dropped == 1 and rec.recheck_skipped == 1


def test_publish_without_date_uses_the_checked_out_bot_branch(content_root):
    class G(FakeGitOps):
        def current_branch(self):
            return "bot/2026-10-24-noon"

    g = G()
    out = []
    assert publish(content_root, g, None, log_out=out.append, slot="noon") == 0
    assert g.calls[-1][:2] == ("publish", "bot/2026-10-24-noon")
    assert "2026-10-24" in g.calls[-1][2]

    class H(FakeGitOps):
        def current_branch(self):
            return "main"

    assert publish(content_root, H(), None, log_out=out.append) == 1
