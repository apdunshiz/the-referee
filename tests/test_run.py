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
    assert c.gitops.calls[:2] == ["auth", ("branch", "bot/2026-10-24")] and c.gitops.calls[-1][0] == "commit"
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
    assert "window" not in c.reddit.calls and ("branch", "bot/2026-10-24") in c.gitops.calls


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
    assert c.reddit.calls == [] and c.gitops.calls == []


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
    assert g.calls == [("publish", "bot/2026-10-24", "Referee: 2026-10-24 (success)")]


def test_slugify_is_stable_and_short():
    s = slugify("Bayesian priors make the resurrection a wash, whatever the evidence says about it.")
    assert s.startswith("bayesian-priors-make-the-resurrection-a-wash-whatever-") and len(s) <= 67
    assert slugify("!!!") .startswith("argument-")
