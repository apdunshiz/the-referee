"""Render the static site from content/ and status.json.

    python site/render.py --out _site [--root .] [--base /the-referee/]

Every content field is rendered through Jinja autoescaping; nothing is marked
safe. Paragraph text (claim ``why``, question bodies) is split on blank lines
and emitted as one escaped <p> per paragraph.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from referee import config, content  # noqa: E402

SITE_DIR = Path(__file__).resolve().parent
REPO_URL = "https://github.com/apdunshiz/the-referee"
STALE_AFTER = timedelta(hours=36)


def paragraphs(text: Optional[str]) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def slug(verdict: str) -> str:
    return "v-" + verdict.lower().replace(" ", "-")


def parse_ts(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def build_today(status: content.Status, sightings: list[content.Sighting], claims_by_id: dict, now: datetime) -> dict:
    """Decide which Today state applies. One state wins; banners stack on top."""
    # "Last run" means the last run that did work; noon no-ops, skips and pauses are not news.
    real_runs = [r for r in status.runs if r.outcome not in ("noop", "skipped", "paused")]
    last_run = real_runs[-1] if real_runs else (status.runs[-1] if status.runs else None)
    last_success = parse_ts(status.last_success)
    stale = last_success is not None and now - last_success > STALE_AFTER
    no_runs = last_run is None and last_success is None

    today_date = (last_success or now).date()
    todays = [s for s in sightings if (parse_ts(s.matched_at) or now).date() == today_date and s.claim_id in claims_by_id]
    grouped: dict[str, list[content.Sighting]] = defaultdict(list)
    for s in todays:
        grouped[s.claim_id].append(s)
    groups = [
        {"claim": claims_by_id[cid], "sightings": sorted(ss, key=lambda s: s.matched_at, reverse=True)}
        for cid, ss in sorted(grouped.items(), key=lambda kv: -len(kv[1]))
    ]

    if last_run is not None and last_run.outcome == "failed":
        state = "error"
    elif status.degraded or (last_run is not None and last_run.outcome == "degraded"):
        state = "degraded"
    elif groups:
        state = "success"
    else:
        state = "empty"

    off_topic = 0
    if last_run is not None:
        off_topic = max(0, last_run.units - last_run.matched - last_run.drafted)
    return {
        "state": state,
        "groups": groups,
        "count": len(todays),
        "off_topic": off_topic,
        "carried": len(status.carried),
        "paused": status.paused,
        "stale": stale,
        "no_runs": no_runs,
        "last_success": last_success,
        "date": today_date,
        "last_run": last_run,
    }


class WorldviewView:
    """A worldview plus the derived numbers the templates show."""

    def __init__(self, w: content.Worldview, criteria: list) -> None:
        self.id = w.id
        self.name = w.name
        self.one_line = w.one_line
        self.core_claim = w.core_claim
        self.scores = w.scores
        self.sources = w.sources
        self.body = w.body
        self.by_criterion = {sc.criterion: sc for sc in w.scores}
        scored = [self.by_criterion[c.id] for c in criteria if c.id in self.by_criterion]
        self.total = sum(sc.score for sc in scored)
        self.max_total = 10 * len(criteria)
        self.avg_confidence = round(sum(sc.confidence for sc in scored) / len(scored)) if scored else 0


def build_worldviews(worldviews: list, criteria: list) -> list:
    """Sort by total descending; ties keep name order."""
    views = [WorldviewView(w, criteria) for w in sorted(worldviews, key=lambda w: w.name)]
    return sorted(views, key=lambda v: -v.total)


def build_proof(evidence_for: list, evidence_against: list, top_n: int = 3) -> dict:
    """The home page's single number: the share of evidence weight that points to God.

    pct = 100 * sum(strength for) / (sum for + sum against). Equal columns read 50%.
    Confidence is the mean confidence of every line. The primary reasons are the
    strongest lines on each side. The method is stated on the page next to the number.
    """
    sum_for = sum(e.strength for e in evidence_for)
    sum_against = sum(e.strength for e in evidence_against)
    total = sum_for + sum_against
    lines = list(evidence_for) + list(evidence_against)
    return {
        "pct": round(100 * sum_for / total) if total else None,
        "sum_for": sum_for,
        "sum_against": sum_against,
        "max_each": 10 * max(len(evidence_for), len(evidence_against)),
        "confidence": round(sum(e.confidence for e in lines) / len(lines)) if lines else None,
        "top_for": evidence_for[:top_n],
        "top_against": evidence_against[:top_n],
    }


def render(root: Path, out: Path, base_url: str = "/", now: Optional[datetime] = None) -> int:
    now = now or datetime.now(timezone.utc)
    root = root.resolve()
    questions = content.load_questions(root)
    claims = content.load_claims(root)
    drafts = content.load_drafts(root)
    sightings = content.load_sightings(root)
    status = content.load_status(root)
    site = content.load_site_data(root)
    evidence = content.load_evidence(root)
    worldviews = build_worldviews(content.load_worldviews(root), site.criteria)
    evidence_for = sorted([e for e in evidence if e.side == "for"], key=lambda e: (-e.strength, e.id))
    evidence_against = sorted([e for e in evidence if e.side == "against"], key=lambda e: (-e.strength, e.id))
    proof = build_proof(evidence_for, evidence_against)

    claims_by_id = {c.id: c for c in claims}
    claims_by_q: dict[str, list[content.Claim]] = defaultdict(list)
    for c in claims:
        claims_by_q[c.question].append(c)
    sightings_by_claim: dict[str, list[content.Sighting]] = defaultdict(list)
    for s in sightings:
        if s.claim_id in claims_by_id:
            sightings_by_claim[s.claim_id].append(s)
    for ss in sightings_by_claim.values():
        ss.sort(key=lambda s: s.matched_at, reverse=True)
    visible_drafts = [d for d in drafts if d.sightings_count >= config.DRAFT_PUBLISH_SIGHTINGS]
    today = build_today(status, sightings, claims_by_id, now)
    tokens_in = sum(r.tokens_in for r in status.runs)
    tokens_out = sum(r.tokens_out for r in status.runs)

    env = Environment(
        loader=FileSystemLoader(str(SITE_DIR / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["paragraphs"] = paragraphs
    env.filters["vslug"] = slug
    env.globals.update(
        base=base_url if base_url.endswith("/") else base_url + "/",
        repo_url=REPO_URL,
        n_questions=len(questions),
        n_claims=len(claims),
        n_evidence=len(evidence),
        n_worldviews=len(worldviews),
        generated=now.strftime("%Y-%m-%d %H:%M UTC"),
        legend=site.legend,
    )

    def write(rel: str, template: str, **ctx) -> None:
        html = env.get_template(template).render(**ctx)
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    pages = 0

    write("index.html", "index.html.j2", questions=questions, site=site, today=today, evidence_for=evidence_for, evidence_against=evidence_against, proof=proof, worldviews=worldviews, criteria=site.criteria)
    pages += 1
    q_by_id = {q.id: q for q in questions}
    for e in evidence:
        write(
            f"evidence/{e.id}/index.html",
            "evidence.html.j2",
            e=e,
            related_questions=[q_by_id[q] for q in e.related_questions if q in q_by_id],
            related_claims=[claims_by_id[c] for c in e.related_claims if c in claims_by_id],
        )
        pages += 1
    write("worldviews/index.html", "worldviews.html.j2", worldviews=worldviews, criteria=site.criteria, site=site)
    pages += 1
    for w in worldviews:
        write(f"worldviews/{w.id}/index.html", "worldview.html.j2", w=w, criteria=site.criteria)
        pages += 1
    write("questions/index.html", "questions.html.j2", questions=questions, site=site)
    pages += 1
    for q in questions:
        write(f"q/{q.id}/index.html", "question.html.j2", q=q, claims=claims_by_q.get(q.id, []), sightings_by_claim=sightings_by_claim)
        pages += 1
    for c in claims:
        write(f"claims/{c.id}/index.html", "claim.html.j2", c=c, q=q_by_id.get(c.question), sightings=sightings_by_claim.get(c.id, []))
        pages += 1
    write("today/index.html", "today.html.j2", today=today, drafts=visible_drafts, status=status)
    write("about/index.html", "about.html.j2", status=status, tokens_in=tokens_in, tokens_out=tokens_out, today=today, history_facts=site.history)
    write("rubric/index.html", "rubric.html.j2", site=site)
    write("404.html", "404.html.j2")
    pages += 4

    status_src = root / "status.json"
    if status_src.exists():
        shutil.copyfile(status_src, out / "status.json")
    else:
        (out / "status.json").write_text(status.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")
    shutil.copytree(SITE_DIR / "static", out / "static", ignore=_static_ignore)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return pages


PUBLISHED_STATIC_SUFFIXES = (".css", ".woff2")
UNPUBLISHED_STATIC_NAMES = {"curl.cfg", "gf.css"}  # font-fetch leftovers, not part of the site


def _static_ignore(directory: str, names: list[str]) -> list[str]:
    """copytree ignore callback: publish only stylesheets and font files."""
    skip = []
    for n in names:
        if (Path(directory) / n).is_dir():
            continue
        if n in UNPUBLISHED_STATIC_NAMES or not n.endswith(PUBLISHED_STATIC_SUFFIXES):
            skip.append(n)
    return skip


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python site/render.py")
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--out", default="_site", type=Path)
    ap.add_argument("--base", "--base-url", dest="base", default="/", help="site root path that prefixes every internal link and asset, e.g. /the-referee/ for project Pages")
    args = ap.parse_args(argv)
    problems = content.validate_tree(args.root.resolve())
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    pages = render(args.root, args.out, args.base)
    print(f"rendered {pages} pages to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
