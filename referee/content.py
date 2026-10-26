"""Content models and file I/O for The Referee.

The pydantic models here are the single schema for everything under
``content/`` and for ``status.json``. ``schema/*.json`` is exported from them
(``python -m referee.content export-schema``) and CI fails when that export is
stale (``--check``). Models forbid unknown keys so a typo in a hand-edited
frontmatter key fails validation instead of being ignored.

Layout (flat, see decision D22):

    content/questions/q01.md            Question frontmatter + body
    content/claims/q01-c01.md           Locked claim (ruling) frontmatter + body
    content/claims/new/<slug>.md        Draft (new-unrated) claim
    content/sightings/<fullname>.json   One sighting per Reddit fullname
    content/evidence/<for|against>-NN.md  One line of evidence for or against God
    content/worldviews/<id>.md          One religion or stance, scored on site.json criteria
    status.json                         Bot status (watermark, counts, last runs)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Iterable, Optional

import frontmatter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTENT_DIR_NAME = "content"
SCHEMA_DIR_NAME = "schema"
FULLNAME_RE = re.compile(r"^t[13]_[a-z0-9]+$")
PERMALINK_RE = re.compile(r"^https://(www\.)?reddit\.com/r/DebateAChristian/")
CLAIM_ID_RE = re.compile(r"^q\d{2}-c\d{2}$")
QUESTION_ID_RE = re.compile(r"^q\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Reddit handles in any of the forms u/name, /u/name, /user/name, reddit.com/u/name,
# reddit.com/user/name. The lookbehind stops "menu/x" from matching; a leading "/" is allowed.
USERNAME_RE = re.compile(r"(?<![A-Za-z0-9_])(?:(?:https?://)?(?:www\.)?reddit\.com)?/?u(?:ser)?/[A-Za-z0-9_-]{3,}", re.IGNORECASE)


def find_usernames(text: str) -> list[str]:
    """Every Reddit handle mention in `text` (decision D15: none may appear in content)."""
    return [m.group(0) for m in USERNAME_RE.finditer(text or "")]


def scrub_usernames(text: str, replacement: str = "another commenter") -> str:
    """Replace handle mentions with a neutral phrase; possessives keep their 's."""
    return USERNAME_RE.sub(replacement, text or "")


def _no_usernames(v):
    items = v if isinstance(v, list) else [v]
    for item in items:
        if isinstance(item, str) and find_usernames(item):
            raise ValueError("usernames are not allowed in content (decision D15)")
    return v


class Verdict(str, Enum):
    TRUE = "TRUE"
    MOSTLY_TRUE = "MOSTLY TRUE"
    MIXED = "MIXED"
    OVERSTATED = "OVERSTATED"
    MOSTLY_FALSE = "MOSTLY FALSE"
    FALSE = "FALSE"
    OPEN = "OPEN"
    STRAWMAN = "STRAWMAN"
    NOTE = "NOTE"


class Side(str, Enum):
    """Who makes the claim. 'theist' covers the original post and Christian commenters."""

    THEIST = "theist"
    SKEPTIC = "skeptic"
    UNSTATED = "unstated"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class HistoryEntry(Strict):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    version: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=300)

    @field_validator("note")
    @classmethod
    def _note_no_usernames(cls, v: str) -> str:
        return _no_usernames(v)


class Question(Strict):
    id: str = Field(pattern=QUESTION_ID_RE.pattern)
    n: int = Field(ge=1, le=99)
    title: str = Field(min_length=3, max_length=120)
    confidence: int = Field(ge=0, le=100, description="How confident the referee is in this question's overall ruling.")
    short: str = Field(min_length=3, max_length=400, description="One-line verdict shown in lists.")
    verdict: str = Field(min_length=3, max_length=1200, description="The question-level ruling, plain text.")
    reply: Optional[str] = Field(default=None, max_length=1500, description="A fair reply a Christian could give; plain text.")
    thread_url: Optional[str] = Field(default=None, pattern=PERMALINK_RE.pattern)
    body: str = ""

    @field_validator("title", "short", "verdict", "reply", "body")
    @classmethod
    def _question_no_usernames(cls, v):
        return _no_usernames(v)

    @model_validator(mode="after")
    def _id_matches_n(self) -> "Question":
        if self.id != f"q{self.n:02d}":
            raise ValueError(f"id {self.id!r} does not match n={self.n}")
        return self


class Claim(Strict):
    """A canonical argument with a ruling. Locked claims change only by human PR."""

    id: str = Field(pattern=CLAIM_ID_RE.pattern)
    question: str = Field(pattern=QUESTION_ID_RE.pattern)
    text: str = Field(min_length=10, max_length=400, description="The claim in neutral words. No usernames, no verbatim quotes.")
    side: Side
    verdict: Verdict
    strength: Optional[int] = Field(default=None, ge=0, le=10, description="How strong the claim is as an argument, 0-10. None for the original post's lines.")
    why: str = Field(min_length=10, max_length=2000, description="The ruling's reasoning, plain text; paragraphs separated by blank lines.")
    sources: list[Annotated[str, Field(min_length=3)]] = Field(default_factory=list, max_length=12)
    confidence: int = Field(ge=0, le=100, description="How confident the referee is that this ruling is right.")
    status: str = Field(default="locked", pattern=r"^locked$")
    version: int = Field(default=1, ge=1)
    history: list[HistoryEntry] = Field(default_factory=list)
    body: str = ""

    @field_validator("text", "why", "body", "sources")
    @classmethod
    def _claim_no_usernames(cls, v):
        return _no_usernames(v)

    @field_validator("text", "why")
    @classmethod
    def _no_html(cls, v: str) -> str:
        if re.search(r"<[a-zA-Z/][^>]*>", v):
            raise ValueError("HTML is not allowed; content is plain text")
        return v

    @model_validator(mode="after")
    def _ids_agree(self) -> "Claim":
        if not self.id.startswith(self.question + "-"):
            raise ValueError(f"claim id {self.id!r} does not belong to question {self.question!r}")
        return self


class Draft(Strict):
    """A new argument the mapper could not match. Carries no verdict (decision D28)."""

    slug: str = Field(pattern=SLUG_RE.pattern, max_length=80)
    text: str = Field(min_length=10, max_length=400)
    side: Side = Side.UNSTATED
    status: str = Field(default="new-unrated", pattern=r"^new-unrated$")
    first_seen: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    sightings_count: int = Field(ge=1)
    # Every permalink ever counted, so a re-processed comment is never counted twice; pages show only a few.
    links: list[str] = Field(default_factory=list, max_length=1000)
    body: str = ""

    @field_validator("links")
    @classmethod
    def _links_are_reddit(cls, v: list[str]) -> list[str]:
        for url in v:
            if not PERMALINK_RE.match(url):
                raise ValueError(f"draft link must be an r/DebateAChristian permalink: {url}")
        return v

    @field_validator("text", "body")
    @classmethod
    def _draft_no_usernames(cls, v):
        return _no_usernames(v)


class Sighting(Strict):
    """A Reddit comment or post matched to a claim. Ids and a link only; no quote text (decision D27)."""

    fullname: str = Field(pattern=FULLNAME_RE.pattern)
    permalink: str = Field(pattern=PERMALINK_RE.pattern)
    claim_id: str = Field(pattern=CLAIM_ID_RE.pattern)
    match_confidence: float = Field(ge=0.0, le=1.0)
    matched_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class RunRecord(Strict):
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    outcome: str = Field(pattern=r"^(success|degraded|failed|paused|skipped|noop)$")
    fetched: int = 0
    units: int = 0
    matched: int = 0
    drafted: int = 0
    invalid_match: int = 0
    quote_rejected: int = 0
    model_refused: int = 0
    draft_rejected: int = 0
    carried: int = 0
    recheck_dropped: int = 0
    recheck_skipped: int = 0
    duration_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    errors: list[str] = Field(default_factory=list)


class Status(Strict):
    watermark: Optional[str] = Field(default=None, description="created_utc (ISO) of the newest unit processed.")
    last_success: Optional[str] = None
    last_step: Optional[str] = None
    paused: bool = False
    degraded: bool = False
    carried: list[str] = Field(default_factory=list, description="Unit fullnames to process first next run.")
    errors: list[str] = Field(default_factory=list)
    runs: list[RunRecord] = Field(default_factory=list, max_length=30)


MODELS: dict[str, type[Strict]] = {
    "question": Question,
    "claim": Claim,
    "draft": Draft,
    "sighting": Sighting,
    "status": Status,
}


# --------------------------------------------------------------------------- I/O


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_nfc(text))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read_markdown(path: Path, model: type[Strict]) -> Strict:
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    data = dict(post.metadata)
    data["body"] = _nfc(post.content.strip())
    return model.model_validate(data)


def _write_markdown(path: Path, obj: Strict) -> None:
    data = obj.model_dump(mode="json", exclude_none=True)
    body = data.pop("body", "") or ""
    post = frontmatter.Post(body, **data)
    _atomic_write(path, frontmatter.dumps(post, sort_keys=False) + "\n")


def question_path(root: Path, qid: str) -> Path:
    return root / CONTENT_DIR_NAME / "questions" / f"{qid}.md"


def claim_path(root: Path, claim_id: str) -> Path:
    return root / CONTENT_DIR_NAME / "claims" / f"{claim_id}.md"


def draft_path(root: Path, slug: str) -> Path:
    return root / CONTENT_DIR_NAME / "claims" / "new" / f"{slug}.md"


def sighting_path(root: Path, fullname: str) -> Path:
    if not FULLNAME_RE.match(fullname):
        raise ValueError(f"refusing to build a path from an invalid fullname: {fullname!r}")
    # gstack-shortcut(dec-SHARD): flat directory; upgrade to YYYY-MM shards when the build exceeds 60 s or 10k files.
    return root / CONTENT_DIR_NAME / "sightings" / f"{fullname}.json"


def load_questions(root: Path) -> list[Question]:
    files = sorted((root / CONTENT_DIR_NAME / "questions").glob("q*.md"))
    return [_read_markdown(p, Question) for p in files]  # type: ignore[misc]


def load_claims(root: Path) -> list[Claim]:
    files = sorted((root / CONTENT_DIR_NAME / "claims").glob("q*-c*.md"))
    return [_read_markdown(p, Claim) for p in files]  # type: ignore[misc]


def load_drafts(root: Path) -> list[Draft]:
    files = sorted((root / CONTENT_DIR_NAME / "claims" / "new").glob("*.md"))
    return [_read_markdown(p, Draft) for p in files]  # type: ignore[misc]


def load_sightings(root: Path) -> list[Sighting]:
    files = sorted((root / CONTENT_DIR_NAME / "sightings").glob("t*_*.json"))
    return [Sighting.model_validate_json(p.read_text(encoding="utf-8")) for p in files]


def load_status(root: Path) -> Status:
    p = root / "status.json"
    if not p.exists():
        return Status()
    return Status.model_validate_json(p.read_text(encoding="utf-8"))


def save_question(root: Path, q: Question) -> Path:
    p = question_path(root, q.id)
    _write_markdown(p, q)
    return p


def save_claim(root: Path, c: Claim) -> Path:
    p = claim_path(root, c.id)
    _write_markdown(p, c)
    return p


def save_draft(root: Path, d: Draft) -> Path:
    p = draft_path(root, d.slug)
    _write_markdown(p, d)
    return p


def save_sighting(root: Path, s: Sighting) -> Path:
    p = sighting_path(root, s.fullname)
    _atomic_write(p, s.model_dump_json(indent=2) + "\n")
    return p


def save_status(root: Path, st: Status) -> Path:
    p = root / "status.json"
    _atomic_write(p, st.model_dump_json(indent=2, exclude_none=True) + "\n")
    return p


def drop_sightings(root: Path, fullnames: Iterable[str]) -> list[str]:
    """Delete sighting files whose source is gone. Returns the fullnames removed."""
    removed = []
    for fn in fullnames:
        p = sighting_path(root, fn)
        if p.exists():
            p.unlink()
            removed.append(fn)
    return removed


# --------------------------------------------------------------------------- validation


def validate_tree(root: Path) -> list[str]:
    """Validate every content file. Returns a list of problems (empty when valid)."""
    problems: list[str] = []
    questions: dict[str, Question] = {}
    for p in sorted((root / CONTENT_DIR_NAME / "questions").glob("*.md")):
        try:
            q = _read_markdown(p, Question)
            questions[q.id] = q  # type: ignore[assignment]
        except Exception as e:  # noqa: BLE001 - we are collecting every problem
            problems.append(f"{p}: {e}")
    claim_ids: set[str] = set()
    for p in sorted((root / CONTENT_DIR_NAME / "claims").glob("*.md")):
        try:
            c = _read_markdown(p, Claim)
            if p.stem != c.id:  # type: ignore[attr-defined]
                problems.append(f"{p}: file name does not match id {c.id!r}")  # type: ignore[attr-defined]
            if c.question not in questions:  # type: ignore[attr-defined]
                problems.append(f"{p}: unknown question {c.question!r}")  # type: ignore[attr-defined]
            claim_ids.add(c.id)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            problems.append(f"{p}: {e}")
    for p in sorted((root / CONTENT_DIR_NAME / "claims" / "new").glob("*.md")):
        try:
            d = _read_markdown(p, Draft)
            if p.stem != d.slug:  # type: ignore[attr-defined]
                problems.append(f"{p}: file name does not match slug {d.slug!r}")  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            problems.append(f"{p}: {e}")
    for p in sorted((root / CONTENT_DIR_NAME / "sightings").glob("*.json")):
        try:
            s = Sighting.model_validate_json(p.read_text(encoding="utf-8"))
            if p.stem != s.fullname:
                problems.append(f"{p}: file name does not match fullname {s.fullname!r}")
            if s.claim_id not in claim_ids:
                problems.append(f"{p}: sighting points at unknown claim {s.claim_id!r}")
        except Exception as e:  # noqa: BLE001
            problems.append(f"{p}: {e}")
    if (root / "status.json").exists():
        try:
            load_status(root)
        except Exception as e:  # noqa: BLE001
            problems.append(f"status.json: {e}")
    if (root / CONTENT_DIR_NAME / "site.json").exists():
        try:
            load_site_data(root)
        except Exception as e:  # noqa: BLE001
            problems.append(f"content/site.json: {e}")
    problems += validate_evidence_and_worldviews(root, set(questions), claim_ids)
    return problems


# --------------------------------------------------------------------------- lock check

BOT_ALLOWED = (
    re.compile(r"^content/sightings/t[13]_[a-z0-9]+\.json$"),
    re.compile(r"^content/claims/new/[a-z0-9-]+\.md$"),
    re.compile(r"^status\.json$"),
)


def lock_check(changed_paths: Iterable[str], actor: str) -> list[str]:
    """Return violations for a diff. ``actor`` is 'bot' or 'human'.

    The bot may only touch sightings, drafts and status.json. A human may touch
    anything; locked-claim edits need a version bump, checked by the caller with
    ``locked_claim_bump_ok``.
    """
    violations = []
    if actor == "bot":
        for path in changed_paths:
            if not any(rx.match(path) for rx in BOT_ALLOWED):
                violations.append(f"bot may not change {path}")
    return violations


def locked_claim_bump_ok(before: Optional[Claim], after: Claim) -> list[str]:
    """A locked claim's content may change only with version+1 and a new history line."""
    if before is None:
        return []
    content_fields = ("text", "side", "verdict", "strength", "why", "sources", "confidence", "body")
    changed = [f for f in content_fields if getattr(before, f) != getattr(after, f)]
    if not changed:
        return []
    problems = []
    if after.version != before.version + 1:
        problems.append(f"{after.id}: content changed ({', '.join(changed)}) but version is {after.version}, expected {before.version + 1}")
    if len(after.history) != len(before.history) + 1:
        problems.append(f"{after.id}: content changed but no history entry was added")
    elif after.history[-1].version != after.version:
        problems.append(f"{after.id}: newest history entry has version {after.history[-1].version}, expected {after.version}")
    return problems


# --------------------------------------------------------------------------- schema export


def export_schemas() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in MODELS.items()}


def write_schemas(root: Path) -> list[Path]:
    out = []
    for name, schema in export_schemas().items():
        p = root / SCHEMA_DIR_NAME / f"{name}.schema.json"
        _atomic_write(p, json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        out.append(p)
    return out


def check_schemas(root: Path) -> list[str]:
    stale = []
    for name, schema in export_schemas().items():
        p = root / SCHEMA_DIR_NAME / f"{name}.schema.json"
        want = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if not p.exists() or p.read_text(encoding="utf-8") != want:
            stale.append(str(p))
    return stale


# --------------------------------------------------------------------------- CLI


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m referee.content")
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    es = sub.add_parser("export-schema", help="write schema/*.json from the models")
    es.add_argument("--check", action="store_true", help="exit 1 if the committed schema is stale")
    sub.add_parser("validate", help="validate every file under content/ and status.json")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "export-schema":
        if args.check:
            stale = check_schemas(root)
            for s in stale:
                print(f"stale: {s}", file=sys.stderr)
            if stale:
                print("schema/ is out of date; run: python -m referee.content export-schema", file=sys.stderr)
            return 1 if stale else 0
        for p in write_schemas(root):
            print(p.relative_to(root))
        return 0
    if args.cmd == "validate":
        problems = validate_tree(root)
        for pr in problems:
            print(pr, file=sys.stderr)
        n_q = len(list((root / CONTENT_DIR_NAME / "questions").glob("*.md")))
        n_c = len(list((root / CONTENT_DIR_NAME / "claims").glob("*.md")))
        n_e = len(list((root / CONTENT_DIR_NAME / "evidence").glob("*.md"))) if (root / CONTENT_DIR_NAME / "evidence").is_dir() else 0
        n_w = len(list((root / CONTENT_DIR_NAME / "worldviews").glob("*.md"))) if (root / CONTENT_DIR_NAME / "worldviews").is_dir() else 0
        print(f"{n_q} questions, {n_c} claims, {n_e} evidence, {n_w} worldviews, {len(problems)} problems")
        return 1 if problems else 0
    return 2



# --------------------------------------------------------------------------- site data (lane S3, appended)


class ScoreboardRow(Strict):
    argument: str = Field(min_length=3, max_length=120)
    as_posted: int = Field(ge=0, le=10, description="Strength of the argument as usually stated, 0-10.")
    best_version: int = Field(ge=0, le=10, description="Strength of the best defensible version, 0-10.")
    weakest_point: str = Field(min_length=3, max_length=400)
    summary: str = Field(min_length=3, max_length=80)

    @field_validator("argument", "weakest_point", "summary")
    @classmethod
    def _row_no_usernames(cls, v):
        return _no_usernames(v)


class LegendRow(Strict):
    verdict: Verdict
    meaning: str = Field(min_length=3, max_length=300)

    @field_validator("meaning")
    @classmethod
    def _legend_no_usernames(cls, v):
        return _no_usernames(v)


class HistoryFact(Strict):
    fact: str = Field(min_length=3, max_length=200)
    pct: int = Field(ge=0, le=100)
    basis: str = Field(min_length=3, max_length=400)

    @field_validator("fact", "basis")
    @classmethod
    def _fact_no_usernames(cls, v):
        return _no_usernames(v)


class Criterion(Strict):
    """One yardstick the worldview comparison scores every worldview on."""

    id: str = Field(pattern=r"^[a-z]+$")
    name: str = Field(min_length=2, max_length=60)
    question: str = Field(min_length=10, max_length=300, description="The question the score answers, in plain words.")

    @field_validator("name", "question")
    @classmethod
    def _criterion_no_usernames(cls, v):
        return _no_usernames(v)


class SiteData(Strict):
    """Home-page data that is not a question or a claim: the scoreboard, the rubric legend,
    the historical-facts table behind 'the big question', and the worldview criteria."""

    scoreboard: list[ScoreboardRow] = Field(min_length=1, max_length=8)
    legend: list[LegendRow] = Field(min_length=1, max_length=12)
    history: list[HistoryFact] = Field(default_factory=list, max_length=12)
    criteria: list[Criterion] = Field(default_factory=list, max_length=8)
    evidence_note: str = Field(default="", max_length=800, description="How to read the evidence lists. No verdict.")
    worldview_note: str = Field(default="", max_length=800, description="How to read the worldview comparison. No verdict.")

    @field_validator("evidence_note", "worldview_note")
    @classmethod
    def _notes_no_usernames(cls, v):
        return _no_usernames(v)

    @model_validator(mode="after")
    def _criteria_unique(self) -> "SiteData":
        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("criteria ids must be unique")
        return self


MODELS["site"] = SiteData


def load_site_data(root: Path) -> SiteData:
    p = root / CONTENT_DIR_NAME / "site.json"
    return SiteData.model_validate_json(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- evidence + worldviews

EVIDENCE_ID_RE = re.compile(r"^(for|against)-\d{2}$")
CRITERION_ID_RE = re.compile(r"^[a-z]+$")
WORLDVIEW_ID_RE = re.compile(r"^[a-z][a-z-]*[a-z]$")


class EvidenceSide(str, Enum):
    FOR = "for"
    AGAINST = "against"


class Evidence(Strict):
    """One line of evidence for or against God, weighed by the same referee and rubric."""

    id: str = Field(pattern=EVIDENCE_ID_RE.pattern)
    side: EvidenceSide
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=400, description="The argument in neutral words.")
    strength: int = Field(ge=0, le=10, description="Weight of the best defensible version as evidence, 0-10.")
    confidence: int = Field(ge=0, le=100, description="How confident the referee is in that strength.")
    status: str = Field(min_length=10, max_length=300, description="Where experts stand, one or two sentences.")
    best_objection: str = Field(min_length=10, max_length=600)
    best_reply: str = Field(min_length=10, max_length=600)
    sources: list[Annotated[str, Field(min_length=3)]] = Field(default_factory=list, max_length=12)
    related_questions: list[str] = Field(default_factory=list)
    related_claims: list[str] = Field(default_factory=list)
    body: str = ""

    @field_validator("title", "summary", "status", "best_objection", "best_reply", "sources", "body")
    @classmethod
    def _evidence_no_usernames(cls, v):
        return _no_usernames(v)

    @field_validator("related_questions")
    @classmethod
    def _questions_shape(cls, v: list[str]) -> list[str]:
        for q in v:
            if not QUESTION_ID_RE.match(q):
                raise ValueError(f"related question id {q!r} is not qNN")
        if len(set(v)) != len(v):
            raise ValueError("related_questions must be unique")
        return v

    @field_validator("related_claims")
    @classmethod
    def _claims_shape(cls, v: list[str]) -> list[str]:
        for c in v:
            if not CLAIM_ID_RE.match(c):
                raise ValueError(f"related claim id {c!r} is not qNN-cNN")
        if len(set(v)) != len(v):
            raise ValueError("related_claims must be unique")
        return v

    @model_validator(mode="after")
    def _id_matches_side(self) -> "Evidence":
        if not self.id.startswith(self.side + "-"):
            raise ValueError(f"evidence id {self.id!r} does not match side {self.side!r}")
        return self


class CriterionScore(Strict):
    criterion: str = Field(pattern=CRITERION_ID_RE.pattern)
    score: int = Field(ge=0, le=10)
    confidence: int = Field(ge=0, le=100)
    why: str = Field(min_length=10, max_length=600)

    @field_validator("why")
    @classmethod
    def _score_no_usernames(cls, v):
        return _no_usernames(v)


class Worldview(Strict):
    """One religion or non-religious stance, scored on every site.json criterion."""

    id: str = Field(pattern=WORLDVIEW_ID_RE.pattern, max_length=40)
    name: str = Field(min_length=2, max_length=60)
    one_line: str = Field(min_length=10, max_length=200)
    core_claim: str = Field(min_length=10, max_length=400)
    scores: list[CriterionScore] = Field(min_length=1, max_length=8)
    sources: list[Annotated[str, Field(min_length=3)]] = Field(default_factory=list, max_length=12)
    body: str = ""

    @field_validator("name", "one_line", "core_claim", "sources", "body")
    @classmethod
    def _worldview_no_usernames(cls, v):
        return _no_usernames(v)

    @model_validator(mode="after")
    def _scores_unique(self) -> "Worldview":
        ids = [sc.criterion for sc in self.scores]
        if len(ids) != len(set(ids)):
            raise ValueError("each criterion may be scored once")
        return self


MODELS["evidence"] = Evidence
MODELS["worldview"] = Worldview


def evidence_path(root: Path, evidence_id: str) -> Path:
    return root / CONTENT_DIR_NAME / "evidence" / f"{evidence_id}.md"


def worldview_path(root: Path, worldview_id: str) -> Path:
    return root / CONTENT_DIR_NAME / "worldviews" / f"{worldview_id}.md"


def load_evidence(root: Path) -> list[Evidence]:
    d = root / CONTENT_DIR_NAME / "evidence"
    if not d.is_dir():
        return []
    return [_read_markdown(p, Evidence) for p in sorted(d.glob("*.md"))]  # type: ignore[misc]


def load_worldviews(root: Path) -> list[Worldview]:
    d = root / CONTENT_DIR_NAME / "worldviews"
    if not d.is_dir():
        return []
    return [_read_markdown(p, Worldview) for p in sorted(d.glob("*.md"))]  # type: ignore[misc]


def save_evidence(root: Path, e: Evidence) -> Path:
    p = evidence_path(root, e.id)
    _write_markdown(p, e)
    return p


def save_worldview(root: Path, w: Worldview) -> Path:
    p = worldview_path(root, w.id)
    _write_markdown(p, w)
    return p


def validate_evidence_and_worldviews(root: Path, question_ids: set[str], claim_ids: set[str]) -> list[str]:
    """Problems in content/evidence and content/worldviews; called from validate_tree."""
    problems: list[str] = []
    for p in sorted((root / CONTENT_DIR_NAME / "evidence").glob("*.md")) if (root / CONTENT_DIR_NAME / "evidence").is_dir() else []:
        try:
            e = _read_markdown(p, Evidence)
            if p.stem != e.id:  # type: ignore[attr-defined]
                problems.append(f"{p}: file name does not match id {e.id!r}")  # type: ignore[attr-defined]
            for q in e.related_questions:  # type: ignore[attr-defined]
                if q not in question_ids:
                    problems.append(f"{p}: unknown related question {q!r}")
            for c in e.related_claims:  # type: ignore[attr-defined]
                if c not in claim_ids:
                    problems.append(f"{p}: unknown related claim {c!r}")
        except Exception as ex:  # noqa: BLE001
            problems.append(f"{p}: {ex}")
    criteria: Optional[set[str]] = None
    if (root / CONTENT_DIR_NAME / "site.json").exists():
        try:
            criteria = {c.id for c in load_site_data(root).criteria}
        except Exception:  # noqa: BLE001 - reported by validate_tree already
            criteria = None
    for p in sorted((root / CONTENT_DIR_NAME / "worldviews").glob("*.md")) if (root / CONTENT_DIR_NAME / "worldviews").is_dir() else []:
        try:
            w = _read_markdown(p, Worldview)
            if p.stem != w.id:  # type: ignore[attr-defined]
                problems.append(f"{p}: file name does not match id {w.id!r}")  # type: ignore[attr-defined]
            if criteria is not None:
                scored = {sc.criterion for sc in w.scores}  # type: ignore[attr-defined]
                for extra in sorted(scored - criteria):
                    problems.append(f"{p}: scores unknown criterion {extra!r}")
                for missing in sorted(criteria - scored):
                    problems.append(f"{p}: missing a score for criterion {missing!r}")
        except Exception as ex:  # noqa: BLE001
            problems.append(f"{p}: {ex}")
    return problems


if __name__ == "__main__":
    raise SystemExit(main())
