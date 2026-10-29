from pathlib import Path

import pytest
from pydantic import ValidationError

from referee import content
from referee.content import Claim, CriterionScore, Draft, Evidence, EvidenceSide, HistoryEntry, Question, Sighting, Side, Verdict, Worldview

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
        "As /u/examplehandle argued, the universe began.",
        "See /user/examplehandle for the thread.",
        "See https://www.reddit.com/u/examplehandle for the thread.",
        "See reddit.com/user/examplehandle for the thread.",
        "As U/examplehandle argued, the universe began.",
        "As /U/examplehandle argued, the universe began.",
        "See Reddit.com/User/examplehandle for the thread.",
    ],
)
def test_find_usernames_catches_every_handle_form(text):
    assert content.find_usernames(text), text
    assert "examplehandle" not in content.scrub_usernames(text) and "someone" not in content.scrub_usernames(text)


def test_find_usernames_ignores_lookalikes():
    assert content.find_usernames("the menu/items list and r/DebateAChristian and https://www.reddit.com/r/DebateAChristian/comments/x/y/") == []


def test_usernames_rejected_in_every_text_field():
    base = dict(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question.")
    for fld in ("title", "short", "verdict", "reply", "body"):
        with pytest.raises(ValidationError):
            Question(**{**base, fld: "Thanks /u/examplehandle for the question"})
    with pytest.raises(ValidationError):
        claim(sources=["Hume (1748)", "u/examplehandle's comment"])
    with pytest.raises(ValidationError):
        claim(body="Notes from reddit.com/user/examplehandle")
    with pytest.raises(ValidationError):
        claim(history=[HistoryEntry(date="2026-10-24", version=1, note="per u/examplehandle")], version=1)
    good = dict(slug="bayesian-priors-wash", text="Bayesian priors make the resurrection a wash.", first_seen="2026-10-24", sightings_count=2)
    with pytest.raises(ValidationError):
        Draft(**good, body="raised by /u/examplehandle")


def test_site_data_rejects_usernames_and_validate_tree_reads_site_json(tmp_path):
    from referee.content import HistoryFact, LegendRow, ScoreboardRow, SiteData

    with pytest.raises(ValidationError):
        ScoreboardRow(argument="Fine-tuning", as_posted=5, best_version=7, weakest_point="Whether the constants could differ", summary="u/examplehandle's strongest")
    with pytest.raises(ValidationError):
        LegendRow(verdict=Verdict.TRUE, meaning="Supported, as /u/examplehandle said.")
    with pytest.raises(ValidationError):
        HistoryFact(fact="Jesus existed", pct=99, basis="See reddit.com/user/examplehandle")
    good = SiteData(scoreboard=[ScoreboardRow(argument="Fine-tuning", as_posted=5, best_version=7, weakest_point="Whether the constants could differ", summary="Strongest")], legend=[LegendRow(verdict=Verdict.TRUE, meaning="Supported.")])
    content.save_question(tmp_path, Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question."))
    (tmp_path / "content" / "site.json").write_text(good.model_dump_json(), encoding="utf-8")
    assert content.validate_tree(tmp_path) == []
    (tmp_path / "content" / "site.json").write_text('{"scoreboard": [], "legend": []}', encoding="utf-8")
    assert any("site.json" in p for p in content.validate_tree(tmp_path))


def evidence(**over):
    base = dict(id="for-01", side=EvidenceSide.FOR, title="The universe had a beginning", summary="Whatever begins to exist has a cause, and the universe began.", strength=6, confidence=70, status="A live position, not an established finding.", best_objection="Quantum gravity may remove the boundary.", best_reply="The theorem still favours a boundary on average.")
    base.update(over)
    return Evidence(**base)


def test_evidence_rejects_side_id_mismatch_and_usernames():
    evidence()
    with pytest.raises(ValidationError):
        evidence(id="against-01")
    with pytest.raises(ValidationError):
        evidence(summary="As u/someone argued, the universe began to exist.")
    with pytest.raises(ValidationError):
        evidence(best_objection="See /u/someone on this, who put it well.")
    with pytest.raises(ValidationError):
        evidence(related_questions=["question-1"])


def test_model_limits_reject_bad_ids_sources_and_duplicate_links():
    sc = CriterionScore(criterion="history", score=5, confidence=60, why="Mixed record on the founding claims.")
    kw = dict(name="Deism", one_line="A creator who does not intervene.", core_claim="God made the world and left it to run.", scores=[sc])
    Worldview(id="deism", **kw)
    for good in ("ab", "ab-cd", "the-referee"):
        Worldview(id=good, **kw)
    for bad in ("-", "a", "-deism", "deism-", "De-ism", "a--b"):
        with pytest.raises(ValidationError):
            Worldview(id=bad, **kw)
    with pytest.raises(ValidationError):
        Worldview(id="deism", sources=[""], **kw)
    with pytest.raises(ValidationError):
        evidence(sources=["x"])
    with pytest.raises(ValidationError):
        claim(sources=[""])
    with pytest.raises(ValidationError):
        evidence(related_questions=["q01", "q01"])
    with pytest.raises(ValidationError):
        evidence(related_claims=["q01-c01", "q01-c01"])


def test_worldview_rejects_duplicate_criterion_and_usernames():
    sc = CriterionScore(criterion="history", score=5, confidence=60, why="Mixed record on the founding claims.")
    Worldview(id="deism", name="Deism", one_line="A creator who does not intervene.", core_claim="God made the world and left it to run.", scores=[sc])
    with pytest.raises(ValidationError):
        Worldview(id="deism", name="Deism", one_line="A creator who does not intervene.", core_claim="God made the world and left it to run.", scores=[sc, sc])
    with pytest.raises(ValidationError):
        CriterionScore(criterion="history", score=5, confidence=60, why="u/someone says the record is mixed.")


def test_validate_tree_checks_evidence_links_and_worldview_criteria(tmp_path):
    content.save_question(tmp_path, Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question."))
    content.save_claim(tmp_path, claim())
    (tmp_path / "content" / "site.json").write_text(
        '{"scoreboard": [{"argument": "The universe began", "as_posted": 4, "best_version": 6, "weakest_point": "A beginning is not settled.", "summary": "Open"}],'
        ' "legend": [{"verdict": "OPEN", "meaning": "Unresolved."}],'
        ' "criteria": [{"id": "history", "name": "Historical evidence", "question": "How well do its founding claims survive scrutiny?"},'
        ' {"id": "coherence", "name": "Internal consistency", "question": "Do its core claims fit together?"}]}',
        encoding="utf-8",
    )
    content.save_evidence(tmp_path, evidence(related_questions=["q09"], related_claims=["q01-c01", "q01-c09"]))
    content.save_worldview(tmp_path, Worldview(id="deism", name="Deism", one_line="A creator who does not intervene.", core_claim="God made the world and left it to run.", scores=[CriterionScore(criterion="history", score=5, confidence=60, why="Mixed record on the founding claims."), CriterionScore(criterion="morals", score=5, confidence=60, why="Not one of the site criteria.")]))
    problems = content.validate_tree(tmp_path)
    assert any("unknown related question 'q09'" in p for p in problems)
    assert any("unknown related claim 'q01-c09'" in p for p in problems)
    assert any("missing a score for criterion 'coherence'" in p for p in problems)
    assert any("scores unknown criterion 'morals'" in p for p in problems)
    assert not any("q01-c01" in p for p in problems)
    assert content.load_evidence(tmp_path)[0].id == "for-01" and content.load_worldviews(tmp_path)[0].id == "deism"
    assert content.load_evidence(tmp_path / "nowhere") == [] and content.load_worldviews(tmp_path / "nowhere") == []


def test_criterion_rule_rejects_usernames():
    from referee.content import Criterion
    Criterion(id="history", name="History", question="Does it hold up?", rule="Start at 5.")
    with pytest.raises(ValidationError):
        Criterion(id="history", name="History", question="Does it hold up?", rule="As u/someone argued.")


NUMBER_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def test_shipped_evidence_shows_arithmetic_that_reaches_its_strength():
    lines = content.load_evidence(ROOT)
    assert lines, "no evidence files found"
    for e in lines:
        assert e.why.startswith("Start at 5."), e.id
        total = 5 + e.why.count("(+1)") - e.why.count("(−1)")
        assert total == e.strength, f"{e.id}: why adds to {total}, strength is {e.strength}"
        assert e.why.rstrip().endswith(NUMBER_WORDS[e.strength] + "."), e.id
