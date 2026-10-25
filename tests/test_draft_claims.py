"""The one-off drafter's safety nets: handle detection on the generated content."""

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("draft_claims", ROOT / "scripts" / "draft_claims.py")
draft_claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft_claims)

# Made-up handles only; the real ones never belong in this public repository.
BUILD_SRC = '''
QUESTIONS = [dict(rulings=[("u/Alpha_Quokka · Atheist", "q", "MIXED", 5, "why"), ("U/beta-wombat77 (Christian) vs. u/Alpha_Quokka", "q", "MIXED", 4, "why")])]
'''


def test_handles_from_build_source_is_case_insensitive():
    assert draft_claims.handles_from_build(BUILD_SRC) == {"Alpha_Quokka", "beta-wombat77"}


def test_scan_finds_bare_handles_and_prefixed_forms(tmp_path):
    (tmp_path / "content" / "claims").mkdir(parents=True)
    (tmp_path / "content" / "claims" / "a.md").write_text("why: alpha_quokka answered directly.", encoding="utf-8")
    (tmp_path / "content" / "claims" / "b.md").write_text("why: see /U/examplehandle", encoding="utf-8")
    (tmp_path / "content" / "claims" / "c.md").write_text("why: nothing here; beta-wombat77abc is not a handle mention", encoding="utf-8")
    hits = draft_claims.scan_content_for_handles(tmp_path, {"Alpha_Quokka", "beta-wombat77"})
    assert hits == {"content/claims/a.md": ["Alpha_Quokka"], "content/claims/b.md": ["/U/examplehandle"]}


def test_scrub_handles_possessive_and_sentence_start():
    out = draft_claims.scrub_usernames("u/Alpha_Quokka's reply was sharp. U/beta-wombat77 made this point well. (u/gamma_newt went on to agree)")
    assert "u/" not in out.lower()
    assert out.startswith("Another commenter's reply")
    assert ". Another commenter made this point" in out and "(One commenter went on to" in out


def test_committed_content_has_no_build_handles():
    build = os.environ.get("REFEREE_BUILD_PY")
    if not build or not Path(build).exists():
        pytest.skip("set REFEREE_BUILD_PY to the review's build.py to run this check")
    assert draft_claims.scan_content_for_handles(ROOT, draft_claims.handles_from_build(Path(build).read_text(encoding="utf-8"))) == {}
