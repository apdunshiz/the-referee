import pytest

from referee import config
from referee.reddit import Credentials, RedditAuthError, RedditClient, RedditRateLimited, RedditUnavailable, units_from
from tests.conftest import FakeResponse, FakeSession, token_ok

CREDS = Credentials("cid", "csecret", "alex", "pw")
NOW = 1_800_000_000.0


def post(i, created, body="x" * 250, removed=False):
    return {"kind": "t3", "data": {"name": f"t3_p{i}", "id": f"p{i}", "title": "A title", "selftext": "[removed]" if removed else body, "created_utc": created, "permalink": f"/r/DebateAChristian/comments/p{i}/t/"}}


def comment(i, body="y" * 250, replies=None, post_id="p1"):
    data = {"name": f"t1_c{i}", "id": f"c{i}", "body": body, "author": "someone", "created_utc": NOW - 100, "link_id": f"t3_{post_id}", "permalink": f"/r/DebateAChristian/comments/{post_id}/t/c{i}/"}
    if replies is not None:
        data["replies"] = {"kind": "Listing", "data": {"children": replies}}
    return {"kind": "t1", "data": data}


def more(children):
    return {"kind": "more", "data": {"children": children}}


def client(responses, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return RedditClient(CREDS, session=FakeSession([token_ok()] + list(responses)), sleep=sleeps.append, now=lambda: NOW), sleeps


def test_fetch_window_pages_until_old():
    page1 = FakeResponse(200, {"data": {"children": [post(1, NOW - 10), post(2, NOW - 20)], "after": "t3_p2"}})
    page2 = FakeResponse(200, {"data": {"children": [post(3, NOW - 30), post(4, NOW - 10 * 86400)], "after": "t3_p4"}})
    c, _ = client([page1, page2])
    posts = c.fetch_window(7)
    assert [p["id"] for p in posts] == ["p1", "p2", "p3"]
    gets = [call for call in c.session.calls if call[0] == "GET"]
    assert len(gets) == 2
    assert gets[1][2]["params"]["after"] == "t3_p2"
    assert gets[0][2]["headers"]["Authorization"] == "bearer secret-token"
    assert gets[0][2]["headers"]["User-Agent"] == "the-referee/0.1 by alex"


def test_rate_limit_sleeps_until_reset_then_aborts():
    r429 = FakeResponse(429, {}, headers={"X-Ratelimit-Reset": "7"})
    c, sleeps = client([r429, r429])
    with pytest.raises(RedditRateLimited):
        c.fetch_window(7)
    assert sleeps == [7.0]


def test_rate_limit_sleep_is_capped():
    r429 = FakeResponse(429, {}, headers={"X-Ratelimit-Reset": "99999"})
    ok = FakeResponse(200, {"data": {"children": [], "after": None}})
    c, sleeps = client([r429, ok])
    assert c.fetch_window(7) == []
    assert sleeps == [float(config.REDDIT_RATELIMIT_SLEEP_CAP_S)]


def test_server_errors_retry_three_times_then_unavailable():
    c, sleeps = client([FakeResponse(503), FakeResponse(502), FakeResponse(500), FakeResponse(500)])
    with pytest.raises(RedditUnavailable):
        c.fetch_window(7)
    assert sleeps == list(config.REDDIT_BACKOFF_S)


def test_token_failure_is_auth_error():
    c = RedditClient(CREDS, session=FakeSession([FakeResponse(401, {"error": "unauthorized"})]), sleep=lambda s: None)
    with pytest.raises(RedditAuthError):
        c.get_token()
    c2 = RedditClient(CREDS, session=FakeSession([FakeResponse(200, {"error": "invalid_grant"})]), sleep=lambda s: None)
    with pytest.raises(RedditAuthError):
        c2.get_token()


def test_removed_and_short_units_are_skipped():
    posts = [post(1, NOW)["data"], post(2, NOW, removed=True)["data"]]
    comments = [comment(1)["data"], comment(2, body="too short")["data"], comment(3, body="[deleted]")["data"]]
    units, dropped = units_from(posts, comments)
    assert [u.fullname for u in units] == ["t3_p1", "t1_c1"]
    assert dropped == 3
    assert units[0].permalink.startswith("https://www.reddit.com/r/DebateAChristian/")


def test_oversize_unit_is_truncated_and_flagged():
    units, _ = units_from([], [comment(1, body="z" * (config.MAX_UNIT_CHARS + 5))["data"]])
    assert units[0].truncated and len(units[0].text) == config.MAX_UNIT_CHARS


def test_fetch_comments_expands_more_stubs():
    tree = FakeResponse(200, [{"data": {"children": []}}, {"data": {"children": [comment(1, replies=[comment(2), more(["c3", "c4"])]), more(["c5"])]}}])
    expansion = FakeResponse(200, {"json": {"data": {"things": [comment(3), comment(4), comment(5), more([])]}}})
    c, _ = client([tree, expansion])
    comments = c.fetch_comments("p1")
    assert sorted(x["id"] for x in comments) == ["c1", "c2", "c3", "c4", "c5"]
    more_call = [call for call in c.session.calls if "morechildren" in call[1]][0]
    assert more_call[2]["params"]["children"] == "c3,c4,c5"
    assert more_call[2]["params"]["link_id"] == "t3_p1"


def test_info_batches_by_100_and_marks_removed():
    names = [f"t1_x{i}" for i in range(150)]
    first = FakeResponse(200, {"data": {"children": [{"kind": "t1", "data": {"name": "t1_x0", "body": "still here"}}, {"kind": "t1", "data": {"name": "t1_x1", "body": "[removed]"}}]}})
    second = FakeResponse(200, {"data": {"children": []}})
    c, _ = client([first, second])
    present = c.info(names)
    gets = [call for call in c.session.calls if "/api/info" in call[1]]
    assert len(gets) == 2
    assert len(gets[0][2]["params"]["id"].split(",")) == 100
    assert present["t1_x0"] is True and present["t1_x1"] is False and present["t1_x149"] is False
