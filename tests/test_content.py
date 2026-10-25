from pathlib import Path

import pytest
from pydantic import ValidationError

from referee import content
from referee.content import Claim, Draft, HistoryEntry, Question, Sighting, Side, Verdict

ROOT = Path(__file__).resolve().parent.parent


def claim(**over):
    base = dict(
        id="q01-c01",
        question="q01",
        text="The universe had a beginning.",
        side=Side.SKEPTIC,
        verdict=Verdict.OPEN,
        strength=5,
        why="A beginning is a live position but not an established finding.",
        sources=["Borde, Guth and Vilenkin (2003)"],
        confidence=90,
    )
    base.update(over)
    return Claim(**base)


def test_claim_rejects_unknown_key():
    with pytest.raises(ValidationError):
        claim(verdcit="OPEN")


def test_claim_rejects_username_and_html():
    with pytest.raises(ValidationError):
        claim(text="As u/someone said, the universe began.")
    with pytest.raises(ValidationError):
        claim(why="Right that a beginning <em>isn't</em> established.")


def test_claim_id_must_belong_to_question():
    with pytest.raises(ValidationError):
        claim(id="q02-c01", question="q01")


def test_draft_rejects_verdict_and_confidence():
    good = dict(slug="bayesian-priors-wash", text="Bayesian priors make the resurrection a wash.", first_seen="2026-10-24", sightings_count=2)
    Draft(**good)
    with pytest.raises(ValidationError):
        Draft(**good, verdict="MIXED")
    with pytest.raises(ValidationError):
        Draft(**good, confidence=80)


def test_sighting_requires_valid_fullname_and_permalink():
    Sighting(fullname="t1_abc123", permalink="https://www.reddit.com/r/DebateAChristian/comments/x/y/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-24T10:00:00Z")
    with pytest.raises(ValidationError):
        Sighting(fullname="../etc/passwd", permalink="https://www.reddit.com/r/DebateAChristian/x", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-24T10:00:00Z")
    with pytest.raises(ValidationError):
        Sighting(fullname="t1_abc", permalink="https://evil.example/", claim_id="q01-c01", match_confidence=0.9, matched_at="2026-10-24T10:00:00Z")


def test_sighting_path_refuses_traversal(tmp_path):
    with pytest.raises(ValueError):
        content.sighting_path(tmp_path, "../x")


def test_question_id_matches_n():
    Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question.")
    with pytest.raises(ValidationError):
        Question(id="q02", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question.")


def test_markdown_roundtrip(tmp_path):
    c = claim(body="Longer notes here.")
    content.save_claim(tmp_path, c)
    [loaded] = content.load_claims(tmp_path)
    assert loaded == c


def test_lock_check_bot_paths():
    ok = ["content/sightings/t1_abc.json", "content/claims/new/some-draft.md", "status.json"]
    assert content.lock_check(ok, "bot") == []
    bad = content.lock_check(["content/claims/q01-c01.md"], "bot")
    assert bad and "may not change" in bad[0]
    assert content.lock_check(["content/claims/q01-c01.md"], "human") == []


def test_locked_claim_bump():
    before = claim()
    unchanged = claim()
    assert content.locked_claim_bump_ok(before, unchanged) == []
    edited_no_bump = claim(why="A different reasoning paragraph that is long enough.")
    assert len(content.locked_claim_bump_ok(before, edited_no_bump)) == 2
    edited_ok = claim(
        why="A different reasoning paragraph that is long enough.",
        version=2,
        history=[HistoryEntry(date="2026-10-24", version=2, note="Clarified the BGV theorem's scope.")],
    )
    assert content.locked_claim_bump_ok(before, edited_ok) == []


def test_validate_tree_catches_orphan_sighting(tmp_path):
    content.save_question(tmp_path, Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question."))
    content.save_claim(tmp_path, claim())
    content.save_sighting(tmp_path, Sighting(fullname="t1_zzz", permalink="https://www.reddit.com/r/DebateAChristian/comments/x/y/", claim_id="q09-c09", match_confidence=0.8, matched_at="2026-10-24T10:00:00Z"))
    problems = content.validate_tree(tmp_path)
    assert any("unknown claim" in p for p in problems)


def test_committed_schema_is_current():
    assert content.check_schemas(ROOT) == [], "run: python -m referee.content export-schema"


def test_committed_content_validates():
    if not (ROOT / "content" / "questions").glob("*.md"):
        pytest.skip("no content yet")
    assert content.validate_tree(ROOT) == []


@pytest.mark.parametrize(
    "text",
    [
        "As u/someone argued, the universe began.",
        "As /u/spezzy argued, the universe began.",
        "See /user/spezzy for the thread.",
        "See https://www.reddit.com/u/spezzy for the thread.",
        "See reddit.com/user/spezzy for the thread.",
    ],
)
def test_find_usernames_catches_every_handle_form(text):
    assert content.find_usernames(text), text
    assert "spezzy" not in content.scrub_usernames(text) and "someone" not in content.scrub_usernames(text)


def test_find_usernames_ignores_lookalikes():
    assert content.find_usernames("the menu/items list and r/DebateAChristian and https://www.reddit.com/r/DebateAChristian/comments/x/y/") == []


def test_usernames_rejected_in_every_text_field():
    base = dict(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question.")
    for fld in ("title", "short", "verdict", "reply", "body"):
        with pytest.raises(ValidationError):
            Question(**{**base, fld: "Thanks /u/spezzy for the question"})
    with pytest.raises(ValidationError):
        claim(sources=["Hume (1748)", "u/spezzy's comment"])
    with pytest.raises(ValidationError):
        claim(body="Notes from reddit.com/user/spezzy")
    with pytest.raises(ValidationError):
        claim(history=[HistoryEntry(date="2026-10-24", version=1, note="per u/spezzy")], version=1)
    good = dict(slug="bayesian-priors-wash", text="Bayesian priors make the resurrection a wash.", first_seen="2026-10-24", sightings_count=2)
    with pytest.raises(ValidationError):
        Draft(**good, body="raised by /u/spezzy")
