import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from referee import content
from referee.content import Claim, Draft, Question, RunRecord, Sighting, Side, Status, Verdict

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
    (root / "content" / "site.json").write_text((ROOT / "content" / "site.json").read_text(encoding="utf-8"), encoding="utf-8")
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
    for rel in ["index.html", "q/q01/index.html", "q/q02/index.html", "claims/q01-c01/index.html", "claims/q02-c02/index.html", "today/index.html", "about/index.html", "rubric/index.html", "404.html", "status.json", "static/tokens.css", ".nojekyll"]:
        assert (out / rel).exists(), rel
    assert pages == 1 + 2 + 4 + 4
    assert "Is there a God? Here's where every argument stands." in read(out, "index.html")


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
    assert 'href="/the-referee/claims/q01-c02/"' in html
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
