import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from referee import content
from referee.content import Claim, CriterionScore, Draft, Evidence, EvidenceSide, Question, RunRecord, Sighting, Side, Status, Verdict, Worldview

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "site"))
import render  # noqa: E402

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
PERMALINK = "https://www.reddit.com/r/DebateAChristian/comments/abc/def/"


def run(**over) -> RunRecord:
    base = dict(run_id="r1", started_at="2026-10-25T10:00:00Z", finished_at="2026-10-25T10:06:00Z", outcome="success", fetched=30, units=100, matched=3, drafted=1)
    base.update(over)
    return RunRecord(**base)


def fixture_tree(root: Path, status: Status | None = None) -> None:
    content.save_question(root, Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="A beginning is a live position.\n\nIt is not an established finding.", reply="Fair point.", body="Intro paragraph."))
    content.save_question(root, Question(id="q02", n=2, title="Does the first cause have to be God?", confidence=90, short="Not shown.", verdict="Overstated."))
    content.save_claim(root, Claim(id="q01-c01", question="q01", text="The evidence points to the universe having a finite past.", side=Side.THEIST, verdict=Verdict.OPEN, strength=None, why="A line from the original post.", confidence=90))
    content.save_claim(root, Claim(id="q01-c02", question="q01", text="Science says nothing about a beginning at all.", side=Side.SKEPTIC, verdict=Verdict.MIXED, strength=5, why="Right that it is not established.\n\nWrong that there is no evidence.", sources=["Borde, Guth and Vilenkin (2003)", "Hostile source <script>alert(1)</script>"], confidence=90))
    content.save_claim(root, Claim(id="q02-c01", question="q02", text="Exempting God from needing a cause is special pleading.", side=Side.SKEPTIC, verdict=Verdict.MOSTLY_FALSE, strength=3, why="The premise is about things that begin to exist.", confidence=90))
    content.save_claim(root, Claim(id="q02-c02", question="q02", text="None of the arguments points to the God of the Bible specifically.", side=Side.SKEPTIC, verdict=Verdict.TRUE, strength=7, why="Arguments one to three reach a creator at best.", confidence=90))
    content.save_draft(root, Draft(slug="bayesian-priors-wash", text="Bayesian priors make the resurrection a wash <script>alert(1)</script>.", first_seen="2026-10-24", sightings_count=2, links=[PERMALINK]))
    content.save_draft(root, Draft(slug="only-once-seen", text="A brand new argument seen only once so far.", first_seen="2026-10-25", sightings_count=1))
    content.save_sighting(root, Sighting(fullname="t1_aaa", permalink=PERMALINK + "1/", claim_id="q01-c02", match_confidence=0.92, matched_at="2026-10-25T10:01:00Z"))
    content.save_sighting(root, Sighting(fullname="t1_bbb", permalink=PERMALINK + "2/", claim_id="q01-c02", match_confidence=0.88, matched_at="2026-10-25T10:02:00Z"))
    content.save_sighting(root, Sighting(fullname="t1_ccc", permalink=PERMALINK + "3/", claim_id="q02-c02", match_confidence=0.81, matched_at="2026-10-20T10:02:00Z"))
    site = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    site["criteria"] = [
        {"id": "history", "name": "Historical evidence", "question": "How well do its founding claims survive historical scrutiny?", "rule": "Start at 5; add 1 per foundation that holds."},
        {"id": "coherence", "name": "Internal consistency", "question": "Do its core claims fit together without contradiction?"},
        {"id": "testable", "name": "Testable claims", "question": "Does it make claims that could in principle be checked?"},
    ]
    site["evidence_note"] = "The columns are not meant to be added up."
    site["worldview_note"] = "Totals are sums of criterion scores, not a ranking of truth."
    (root / "content" / "site.json").write_text(json.dumps(site, indent=2), encoding="utf-8")
    content.save_evidence(root, Evidence(id="for-01", side=EvidenceSide.FOR, title="The universe had a beginning", summary="Whatever begins to exist has a cause, and the universe began.", strength=6, confidence=70, status="A beginning is a live position in cosmology, not an established finding.", best_objection="Quantum gravity may remove the boundary <script>alert(1)</script>.", best_reply="The theorem still favours a boundary on average.", sources=["Borde, Guth and Vilenkin (2003)"], related_questions=["q01"], related_claims=["q01-c02"], body="A longer treatment.\n\nSecond paragraph."))
    content.save_evidence(root, Evidence(id="against-01", side=EvidenceSide.AGAINST, title="The problem of evil", summary="Gratuitous suffering is hard to square with an all-good, all-powerful God.", strength=8, confidence=80, status="The logical version is widely thought answered; the evidential version is live.", best_objection="Skeptical theism says we cannot judge what reasons God might have.", best_reply="That reply also undercuts our ability to read God's goodness from anything.", related_questions=["q02"]))
    content.save_worldview(root, Worldview(id="naturalism", name="Naturalism", one_line="Only the physical world exists; no gods.", core_claim="Nature is all there is and all explanations are ultimately physical.", scores=[CriterionScore(criterion="history", score=9, confidence=80, why="It makes no historical founding claims to defend."), CriterionScore(criterion="coherence", score=8, confidence=75, why="Internally consistent, though consciousness is a strain <script>alert(1)</script>."), CriterionScore(criterion="testable", score=9, confidence=85, why="Its claims are checkable in principle.")], sources=["Papineau, Naturalism (2020)"]))
    content.save_worldview(root, Worldview(id="christianity", name="Christianity", one_line="Jesus of Nazareth rose from the dead and is God incarnate.", core_claim="One God, revealed in Jesus, whose resurrection vindicates his claims.", scores=[CriterionScore(criterion="history", score=6, confidence=70, why="Crucifixion and early belief in appearances are well attested; the rest is contested."), CriterionScore(criterion="coherence", score=6, confidence=60, why="Trinity and incarnation are coherent on some readings and strained on others."), CriterionScore(criterion="testable", score=4, confidence=65, why="Most claims are historical, a few are checkable.")]))
    if status is not None:
        content.save_status(root, status)


def read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


def success_status() -> Status:
    return Status(watermark="2026-10-25T10:00:00Z", last_success="2026-10-25T10:06:00Z", runs=[run()])


def test_every_page_type_renders(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    pages = render.render(tmp_path, out, now=NOW)
    for rel in ["index.html", "q/q01/index.html", "q/q02/index.html", "claims/q01-c01/index.html", "claims/q02-c02/index.html", "today/index.html", "about/index.html", "rubric/index.html", "404.html", "status.json", "static/tokens.css", ".nojekyll", "evidence/for-01/index.html", "evidence/against-01/index.html", "worldviews/index.html", "worldviews/naturalism/index.html", "worldviews/christianity/index.html", "questions/index.html"]:
        assert (out / rel).exists(), rel
    assert pages == 1 + 2 + 4 + 4 + 2 + 1 + 2 + 1
    assert "Is there a God? Here is the evidence, both ways." in read(out, "index.html")


def test_content_is_escaped(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    # The Claim model already refuses HTML in text/why; sources and draft text are the
    # fields that can still carry angle brackets, so they prove the autoescape.
    for rel in ["claims/q01-c02/index.html", "q/q01/index.html", "today/index.html", "index.html"]:
        html = read(out, rel)
        assert "<script>alert(1)</script>" not in html, rel
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in read(out, "claims/q01-c02/index.html")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in read(out, "today/index.html")


def test_claim_page_details(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "claims/q01-c02/index.html")
    assert 'aria-label="90 percent confidence in this ruling"' in html
    assert "5/10" in html
    assert "seen 2× on r/DebateAChristian" in html
    assert "Borde, Guth and Vilenkin (2003)" in html
    assert "<p>Right that it is not established.</p>" in html and "<p>Wrong that there is no evidence.</p>" in html
    assert "https://github.com/apdunshiz/the-referee/blob/main/content/claims/q01-c02.md" in html
    unseen = read(out, "claims/q01-c01/index.html")
    assert "Not yet seen on Reddit since launch." in unseen
    assert "original post" in unseen


def test_today_success_state_groups_by_claim(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "today/index.html")
    assert "matched 2× today" in html
    assert "Science says nothing about a beginning" in html
    assert "None of the arguments points to the God of the Bible" not in html  # sighting from an earlier day
    assert "Nothing new matched today" not in html
    assert '<ul class="today">' in html


def test_today_empty_state(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-25T10:06:00Z", runs=[run(matched=0, drafted=0, units=7)]))
    for p in (tmp_path / "content" / "sightings").glob("*.json"):
        p.unlink()
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert "Nothing new matched today. 7 posts were off-topic." in read(out, "today/index.html")


def test_today_error_state(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-24T10:06:00Z", runs=[run(outcome="failed", errors=["RedditUnavailable"])]))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "today/index.html")
    assert "Reddit couldn't be reached around 06:00 ET; retrying at 12:00." in html
    assert "Last update: 2026-10-24 10:06 UTC" in html


def test_today_degraded_state(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-25T10:06:00Z", degraded=True, carried=["t1_x", "t1_y", "t1_z"], runs=[run(outcome="degraded")]))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert "3 arguments carried to tomorrow." in read(out, "today/index.html")


def test_today_paused_and_stale_banners(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-22T10:06:00Z", paused=True, runs=[run(started_at="2026-10-22T10:00:00Z")]))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "today/index.html")
    assert "Updates paused by the maintainer." in html
    assert "No update since 2026-10-22." in html
    assert "Updates paused by the maintainer." in read(out, "about/index.html")


def test_no_runs_yet(tmp_path):
    fixture_tree(tmp_path)
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert "No runs yet." in read(out, "today/index.html")
    assert "No runs yet." in read(out, "about/index.html")


def test_drafts_need_two_sightings_and_carry_no_percent(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "today/index.html")
    assert "Bayesian priors make the resurrection a wash" in html
    assert "A brand new argument seen only once so far." not in html
    draft_block = html[html.index("New arguments, not yet rated"):]
    assert "DRAFT" in draft_block
    assert "% confident" not in draft_block


def test_no_usernames_anywhere(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    for p in out.rglob("*.html"):
        assert not re.search(r"(^|[^\w/])u/[A-Za-z0-9_-]{3,}", p.read_text(encoding="utf-8")), p


def test_status_json_copied_through(tmp_path):
    st = success_status()
    fixture_tree(tmp_path, st)
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert json.loads(read(out, "status.json"))["last_success"] == "2026-10-25T10:06:00Z"


def test_base_prefixes_links_and_assets(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, base_url="/the-referee/", now=NOW)
    html = read(out, "index.html")
    assert 'href="/the-referee/static/tokens.css?v=' in html
    assert 'href="/the-referee/today/"' in html
    assert 'href="/the-referee/claims/q01-c02/"' in read(out, "today/index.html")  # the home Today block is collapsed to a count + link
    assert 'href="/today/"' not in html and 'href="/static/' not in html
    claim = read(out, "claims/q01-c02/index.html")
    assert 'href="/the-referee/q/q01/"' in claim
    # default base stays root-relative
    render.render(tmp_path, out, now=NOW)
    assert 'href="/static/tokens.css?v=' in read(out, "index.html")


def test_about_history_and_runs(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-25T10:06:00Z", runs=[run(tokens_in=120000, tokens_out=9000)]))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "about/index.html")
    assert "Jesus existed" in html and "99%" in html
    assert "120,000 in, 9,000 out" in html


def test_real_repo_content_renders_fast(tmp_path):
    out = tmp_path / "_site"
    t0 = time.perf_counter()
    proc = subprocess.run([sys.executable, str(ROOT / "site" / "render.py"), "--root", str(ROOT), "--out", str(out), "--base", "/the-referee/"], capture_output=True, text=True, timeout=60)
    elapsed = time.perf_counter() - t0
    assert proc.returncode == 0, proc.stderr
    assert elapsed < 10, f"render took {elapsed:.1f}s"
    n_q = len(list((ROOT / "content" / "questions").glob("q*.md")))
    n_c = len(list((ROOT / "content" / "claims").glob("q*-c*.md")))
    assert n_q == 15 and n_c == 119
    assert len(list((out / "q").iterdir())) == n_q
    assert len(list((out / "claims").iterdir())) == n_c
    assert "rendered" in proc.stdout


def test_static_copy_publishes_only_css_and_fonts(tmp_path):
    out = tmp_path / "_site"
    render.render(ROOT, out)
    names = {p.name for p in (out / "static").rglob("*") if p.is_file()}
    assert "curl.cfg" not in names and "gf.css" not in names
    assert "tokens.css" in names and "local.css" in names and any(n.endswith(".woff2") for n in names)


def test_today_last_run_skips_noon_noops(tmp_path):
    fixture_tree(tmp_path, Status(last_success="2026-10-25T10:06:00Z", runs=[run(), run(run_id="n1", started_at="2026-10-25T16:00:00Z", outcome="noop", fetched=0, units=0, matched=0, drafted=0)]))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "today/index.html")
    assert "Last run 2026-10-25 10:00 UTC: success" in html and "noop" not in html


def test_home_shows_both_evidence_columns_ordered_by_strength(tmp_path):
    fixture_tree(tmp_path, success_status())
    content.save_evidence(tmp_path, Evidence(id="for-02", side=EvidenceSide.FOR, title="Fine-tuning of the constants", summary="The constants sit in a narrow life-permitting range.", strength=7, confidence=80, status="The sensitivity is mainstream physics; its meaning is unresolved.", best_objection="No probability distribution over the constants is known.", best_reply="Physicists use the ranges their theories treat as natural."))
    content.save_evidence(tmp_path, Evidence(id="against-02", side=EvidenceSide.AGAINST, title="Divine hiddenness", summary="A loving God would make himself known to every open seeker.", strength=6, confidence=75, status="Taken seriously by theists; not accepted as decisive by either side.", best_objection="God may keep a distance so belief stays free.", best_reply="Clear evidence does not coerce love."))
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "index.html")
    assert "Evidence for God" in html and "Evidence against God" in html
    for href in ['href="/evidence/for-01/"', 'href="/evidence/for-02/"', 'href="/evidence/against-01/"', 'href="/evidence/against-02/"']:
        assert href in html, href
    assert "Summed strength" not in html  # the note says the columns are not to be added up
    assert html.index("Fine-tuning of the constants") < html.index("The universe had a beginning")  # 7 before 6
    assert html.index("The problem of evil") < html.index("Divine hiddenness")  # 8 before 6
    assert "The columns are not meant to be added up." in html
    assert "Scoreboard: the main arguments" not in html  # moved to /questions/
    assert "Scoreboard: the main arguments" in read(out, "questions/index.html")


def test_matrix_sorted_by_total_with_right_totals(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "index.html")
    assert html.index("Naturalism") < html.index("Christianity")
    assert "26/30" in html and "16/30" in html
    full = read(out, "worldviews/index.html")
    assert full.index('href="/worldviews/naturalism/"') < full.index('href="/worldviews/christianity/"')
    assert "26/30" in full and "16/30" in full and "80%" in full  # avg confidence of naturalism
    # confidence is visible in every matrix cell, not only in a title attribute
    cell = '<b>9</b><span class="cell-conf"><span class="vh">confidence </span>80%</span>'
    assert cell in html and cell in full
    assert "<caption>" in html and "<caption>" in full and "<caption>" in read(out, "worldviews/naturalism/index.html")
    assert 'aria-label="score 9 out of 10"' in read(out, "worldviews/naturalism/index.html")
    assert 'percent confidence in this score' in read(out, "evidence/for-01/index.html")
    assert "Historical evidence" in full and "How well do its founding claims survive historical scrutiny?" in full
    assert "Totals are sums of criterion scores" in full


def test_evidence_and_worldview_pages_render_escaped(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    ev = read(out, "evidence/for-01/index.html")
    assert "<script>alert(1)</script>" not in ev and "&lt;script&gt;alert(1)&lt;/script&gt;" in ev
    assert "Strongest objection" in ev and "Best reply" in ev and "Where experts stand" in ev
    assert 'href="/q/q01/"' in ev and 'href="/claims/q01-c02/"' in ev
    assert "Second paragraph." in ev and "content/evidence/for-01.md" in ev
    wv = read(out, "worldviews/naturalism/index.html")
    assert "<script>alert(1)</script>" not in wv and "&lt;script&gt;alert(1)&lt;/script&gt;" in wv
    assert "Total 26 of 30" in wv and "Nature is all there is" in wv and "content/worldviews/naturalism.md" in wv
    assert "<script>alert(1)</script>" not in read(out, "index.html")


def test_nav_links_carry_base(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, base_url="/the-referee/", now=NOW)
    html = read(out, "index.html")
    for href in ["/the-referee/#evidence", "/the-referee/worldviews/", "/the-referee/questions/", "/the-referee/today/", "/the-referee/evidence/for-01/", "/the-referee/worldviews/naturalism/"]:
        assert f'href="{href}"' in html, href
    assert 'href="/worldviews/"' not in html and 'href="/questions/"' not in html
    for rel in ["evidence/for-01/index.html", "worldviews/naturalism/index.html", "worldviews/index.html"]:
        page = read(out, rel)
        assert 'href="/the-referee/' in page and 'href="/"' not in page and 'href="/q/' not in page and 'href="/static/' not in page, rel
    ev = read(out, "evidence/for-01/index.html")
    assert 'href="/the-referee/q/q01/"' in ev and 'href="/the-referee/claims/q01-c02/"' in ev
    assert 'href="/the-referee/worldviews/"' in read(out, "worldviews/naturalism/index.html")


def test_validate_tree_flags_misnamed_files_and_missing_criterion(tmp_path):
    fixture_tree(tmp_path, success_status())
    content.evidence_path(tmp_path, "for-01").rename(content.evidence_path(tmp_path, "for-09"))
    content.worldview_path(tmp_path, "naturalism").rename(content.worldview_path(tmp_path, "physicalism"))
    wv = content.worldview_path(tmp_path, "christianity")
    text = wv.read_text(encoding="utf-8")
    cut = text.replace("- criterion: testable\n", "- criterion: history\n", 1) if "- criterion: testable\n" in text else text
    assert cut != text
    wv.write_text(cut, encoding="utf-8")
    problems = content.validate_tree(tmp_path)
    assert any("for-09.md: file name does not match id 'for-01'" in p for p in problems)
    assert any("physicalism.md: file name does not match id 'naturalism'" in p for p in problems)
    assert any("christianity.md" in p and "each criterion may be scored once" in p for p in problems)
    wv.write_text(text.replace("- criterion: testable\n  score: 4\n  confidence: 65\n  why: Most claims are historical, a few are checkable.\n", ""), encoding="utf-8")
    problems = content.validate_tree(tmp_path)
    assert any("christianity.md: missing a score for criterion 'testable'" in p for p in problems)


def test_home_without_evidence_or_worldviews_renders(tmp_path):
    fixture_tree(tmp_path, success_status())
    for p in (tmp_path / "content" / "evidence").glob("*.md"):
        p.unlink()
    for p in (tmp_path / "content" / "worldviews").glob("*.md"):
        p.unlink()
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert read(out, "index.html").count("None written yet.") == 3


def test_criterion_rules_render_on_both_worldview_pages(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    assert "How it is scored: Start at 5; add 1 per foundation that holds." in read(out, "worldviews/index.html")
    pages = sorted((out / "worldviews").glob("*/index.html"))
    assert pages
    for wv in pages:
        assert "How it is scored: Start at 5; add 1 per foundation that holds." in wv.read_text(encoding="utf-8")


def test_proof_percentage_and_primary_reasons(tmp_path):
    fixture_tree(tmp_path, success_status())
    out = tmp_path / "_site"
    render.render(tmp_path, out, now=NOW)
    html = read(out, "index.html")
    # fixture: for 6, against 8 -> 43% of the weight points to God
    assert "Proof of God, as a percentage" in html
    assert 'aria-label="43 percent">43%</span>' in html
    assert "(6 for, 8 against)" in html
    # each side's own score: strength over the most it could have (one line each in the fixture)
    assert '<span class="side-num">60%</span>' in html and '<span class="side-num">80%</span>' in html
    assert 'Evidence for God <span class="col-pct">60%</span>' in html
    assert "Primary reasons for" in html and "Primary reasons against" in html
    assert html.index("The universe had a beginning</a> <span class=\"pct\">6/10") > html.index("Primary reasons for")


def test_proof_is_fifty_when_columns_weigh_the_same():
    from types import SimpleNamespace as N
    pf = [N(strength=6, confidence=70, id="for-01", title="a")]
    pa = [N(strength=6, confidence=80, id="against-01", title="b")]
    proof = render.build_proof(pf, pa)
    assert proof["pct"] == 50 and proof["confidence"] == 75 and proof["top_for"] == pf
    assert proof["pct_for"] == 60 and proof["pct_against"] == 60 and proof["max_for"] == 10
    assert render.build_proof([], [])["pct"] is None
