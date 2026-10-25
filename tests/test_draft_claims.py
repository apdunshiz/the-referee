"""The one-off drafter's safety nets: handle detection on the generated content."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("draft_claims", ROOT / "scripts" / "draft_claims.py")
draft_claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft_claims)

BUILD_SRC = '''
QUESTIONS = [dict(rulings=[("u/Korach · Atheist", "q", "MIXED", 5, "why"), ("u/mtruitt76 (Christian) vs. u/Korach", "q", "MIXED", 4, "why")])]
'''


def test_handles_from_build_source():
    assert draft_claims.handles_from_build(BUILD_SRC) == {"Korach", "mtruitt76"}


def test_scan_finds_bare_handles_and_prefixed_forms(tmp_path):
    (tmp_path / "content" / "claims").mkdir(parents=True)
    (tmp_path / "content" / "claims" / "a.md").write_text("why: Korach answered directly.", encoding="utf-8")
    (tmp_path / "content" / "claims" / "b.md").write_text("why: see /u/spezzy", encoding="utf-8")
    (tmp_path / "content" / "claims" / "c.md").write_text("why: nothing here; mtruitt76abc is not a handle mention", encoding="utf-8")
    hits = draft_claims.scan_content_for_handles(tmp_path, {"Korach", "mtruitt76"})
    assert hits == {"content/claims/a.md": ["Korach"], "content/claims/b.md": ["/u/spezzy"]}


def test_scrub_handles_possessive_and_sentence_start():
    out = draft_claims.scrub_usernames("u/Ender505's reply was sharp. u/Korach made this point well. (u/Flokitoo went on to agree)")
    assert "u/" not in out
    assert out.startswith("Another commenter's reply")
    assert ". Another commenter made this point" in out and "(One commenter went on to" in out


def test_committed_content_has_no_build_handles():
    build = Path("/Users/aplevell/.t3/scratch/2026-10-21-a-while-ago-you-helped-ad53e7c0/scripts/build.py")
    if not build.exists():
        import pytest

        pytest.skip("review scratch dir not present")
    assert draft_claims.scan_content_for_handles(ROOT, draft_claims.handles_from_build(build.read_text(encoding="utf-8"))) == {}
