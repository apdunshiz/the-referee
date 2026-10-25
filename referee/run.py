"""The daily run: a fixed sequence of steps with one top-level handler.

    prepare  preflight -> fetch -> map -> dedupe -> recheck -> write -> validate -> commit
    publish  push -> gh pr create -> gh pr merge --auto

The workflow runs ``prepare``, then mints a fresh GitHub App token, then runs
``publish`` (also after a failed prepare) so a failed run still publishes its
status.json and the Today banner can show the error. The bot branch
(``bot/<date>-<slot>``, one per slot) is created before any step can fail, so a
failure never commits on main. Nothing under content/ is written before mapping
completes; a failure at write, validate or commit discards the content changes,
restores status.json from the pre-write snapshot, and commits the failure record
only. The watermark and last_success only move when validate and commit passed.

Noon policy (``--slot noon``): a full run when the morning run failed or was
skipped, carried units only when it was degraded, and a no-op when it succeeded
or was paused.

Log lines are JSON on stdout with run_id, step, fullname, outcome and ms. Quotes,
unit text, headers and tokens are never logged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from . import config, content
from .content import Draft, RunRecord, Sighting, Status
from .mapper import BudgetExhausted, DraftCandidate, MapperBadOutput, MapperRateLimited, MapperTimeout
from .reddit import RedditGone, RedditRateLimited, RedditUnavailable, Unit, units_from

try:  # per-unit API errors are carried, not fatal; tests run without the SDK's network layer
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]


class RunFailed(Exception):
    pass


class ContentInvalid(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def slugify(text: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    slug = "-".join(words[:8])[:60].strip("-")
    if not slug:
        slug = "argument"
    return slug + "-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]


@dataclass
class Context:
    root: Path
    slot: str
    reddit: Any
    mapper: Any
    gitops: Any
    env: dict
    dry_run: bool = False
    since: Optional[str] = None
    only: Optional[str] = None
    now: Callable[[], datetime] = _utcnow
    log_out: Callable[[str], None] = lambda s: print(s, flush=True)
    # state
    status: Status = field(default_factory=Status)
    record: Optional[RunRecord] = None
    date: str = ""
    branch: str = ""
    mode: str = "full"  # full | carried-only
    units: list = field(default_factory=list)
    sightings: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    merged: list = field(default_factory=list)
    to_existing: dict = field(default_factory=dict)
    to_drop: list = field(default_factory=list)
    carried: list = field(default_factory=list)
    new_watermark: Optional[str] = None
    exit_code: Optional[int] = None  # set by a step that ends the run early
    current_unit: Optional[str] = None
    branch_ready: bool = False  # the bot branch exists locally; only then may the handler commit
    status_snapshot: Optional[Status] = None  # status.json as it was before step_write

    def log(self, step: str, outcome: str, **fields: Any) -> None:
        rec = {"ts": _iso(self.now()), "run_id": self.record.run_id if self.record else "", "step": step, "outcome": outcome}
        for k, v in fields.items():
            if k in ("text", "quote", "headers", "token", "body"):
                continue
            rec[k] = v
        self.log_out(json.dumps(rec, ensure_ascii=False))


# --------------------------------------------------------------------------- steps


def bot_branch(date: str, slot: str) -> str:
    """One branch per slot: the noon run must not collide with a morning PR that is still open."""
    return f"bot/{date}-{slot}"


def step_branch(ctx: Context) -> None:
    """Create bot/<date>-<slot> from origin/main before anything can fail, so a failure never commits on main."""
    ctx.date = ctx.now().strftime("%Y-%m-%d")
    ctx.branch = bot_branch(ctx.date, ctx.slot)
    if not ctx.dry_run:
        ctx.gitops.branch_from_main(ctx.branch)
        ctx.branch_ready = True


def _end_early(ctx: Context, outcome: str, message: str) -> None:
    """Record a run that stops before mapping (paused, noop, skipped) so the noon check and About page see it."""
    ctx.record.outcome = outcome
    ctx.exit_code = 0
    if not ctx.dry_run:
        _finish_status(ctx)
        ctx.gitops.commit_all(message)


def step_preflight(ctx: Context) -> None:
    ctx.status = content.load_status(ctx.root)
    if ctx.env.get("INGEST_ENABLED", "true").lower() == "false":
        ctx.status.paused = True
        ctx.log("preflight", "paused")
        _end_early(ctx, "paused", f"Referee: {ctx.date} paused")
        return
    ctx.status.paused = False
    if ctx.slot == "noon":
        last = ctx.status.runs[-1] if ctx.status.runs else None
        if last is None or last.started_at[:10] != ctx.date:
            ctx.log("preflight", "no-morning-run", reason="no run recorded today; full run")
        elif last.outcome in ("success", "noop", "paused"):
            ctx.log("preflight", "noop", reason=f"morning run {last.outcome}")
            _end_early(ctx, "noop", f"Referee: {ctx.date} noon no-op")
            return
        elif last.outcome == "degraded":
            ctx.mode = "carried-only"
        else:
            # failed, or skipped because a bot PR was still open: the noon slot is the retry.
            ctx.log("preflight", "full-run", reason=f"morning run {last.outcome}")
    ctx.gitops.preflight_auth()
    open_prs = ctx.gitops.open_bot_prs()
    if open_prs and not ctx.dry_run:
        number, branch = open_prs[0]
        ctx.gitops.comment_pr(number, f"Run {ctx.date} {ctx.slot} skipped: this bot PR is still open. Fix or close it; the next run will proceed.")
        ctx.log("preflight", "skipped", pr=number, branch=branch)
        _end_early(ctx, "skipped", f"Referee: {ctx.date} {ctx.slot} skipped: bot PR #{number} still open")
        return
    ctx.reddit.get_token()
    ctx.log("preflight", "ok", mode=ctx.mode)


def step_fetch(ctx: Context) -> None:
    posts = ctx.reddit.fetch_window(config.WINDOW_DAYS)
    comments: list[dict] = []
    gone = 0
    for p in posts:
        try:
            comments.extend(ctx.reddit.fetch_comments(p.get("id", "")))
        except RedditGone:
            gone += 1
    units, dropped = units_from(posts, comments)
    ctx.record.fetched = len(posts) + len(comments)
    existing = {p.stem for p in (ctx.root / "content" / "sightings").glob("t*_*.json")}
    carried = set(ctx.status.carried)
    since = ctx.since or ctx.status.watermark
    since_ts = _parse_iso(since).timestamp() if since else 0.0
    selected: list[Unit] = []
    for u in units:
        if ctx.only and u.fullname != ctx.only:
            continue
        if u.fullname in existing:
            continue
        if ctx.mode == "carried-only" and u.fullname not in carried:
            continue
        if u.fullname in carried or u.created_utc > since_ts:
            selected.append(u)
    selected.sort(key=lambda u: (u.fullname not in carried, u.created_utc))
    ctx.units = selected
    ctx.record.units = len(selected)
    ctx.log("fetch", "ok", posts=len(posts), comments=len(comments), units=len(selected), dropped=dropped, gone=gone)


def step_map(ctx: Context) -> None:
    failures = 0
    processed_ts: list[float] = []
    remaining = list(ctx.units)
    while remaining:
        u = remaining.pop(0)
        ctx.current_unit = u.fullname
        t0 = time.monotonic()
        try:
            out = ctx.mapper.map_unit(u)
        except BudgetExhausted:
            ctx.carried.append(u.fullname)
            ctx.carried.extend(x.fullname for x in remaining)
            ctx.log("map", "budget_exhausted", carried=len(ctx.carried))
            remaining = []
            break
        except (MapperRateLimited, MapperTimeout, MapperBadOutput) as e:
            failures += 1
            ctx.carried.append(u.fullname)
            ctx.log("map", "carried", fullname=u.fullname, error=type(e).__name__, ms=int((time.monotonic() - t0) * 1000))
            continue
        except Exception as e:  # noqa: BLE001 - only the SDK's own errors are carried; anything else is a bug
            if anthropic is None or not isinstance(e, anthropic.APIError):
                raise
            failures += 1
            ctx.carried.append(u.fullname)
            ctx.log("map", "carried", fullname=u.fullname, error=type(e).__name__, ms=int((time.monotonic() - t0) * 1000))
            continue
        processed_ts.append(u.created_utc)
        ms = int((time.monotonic() - t0) * 1000)
        if out.outcome == "matched":
            ctx.sightings.append(out.sighting)
            ctx.record.matched += 1
        elif out.outcome == "new_argument":
            ctx.candidates.append(DraftCandidate(text=out.draft_text, units=[u]))
        elif out.outcome == "invalid_match":
            ctx.record.invalid_match += 1
        elif out.outcome == "quote_rejected":
            ctx.record.quote_rejected += 1
        elif out.outcome == "refused":
            ctx.record.model_refused += 1
        elif out.outcome == "draft_rejected":
            ctx.record.draft_rejected += 1
        ctx.log("map", out.outcome, fullname=u.fullname, claim_id=out.claim_id, confidence=round(out.match_confidence, 3), ms=ms)
    ctx.current_unit = None
    n = len(ctx.units)
    if n and failures == n:
        raise RunFailed(f"mapper failed for every unit ({n})")
    ctx.status.degraded = bool(n) and failures > config.DEGRADED_FAILURE_RATIO * n
    if processed_ts:
        ctx.new_watermark = _iso(datetime.fromtimestamp(max(processed_ts), tz=timezone.utc))
    ctx.record.carried = len(ctx.carried)
    ctx.record.tokens_in = getattr(ctx.mapper, "used_in", 0)
    ctx.record.tokens_out = getattr(ctx.mapper, "used_out", 0)


def step_dedupe(ctx: Context) -> None:
    existing = [(d.slug, d.text) for d in content.load_drafts(ctx.root)]
    ctx.merged, ctx.to_existing = ctx.mapper.dedupe_pass(ctx.candidates, existing)
    ctx.record.drafted = len(ctx.merged)
    ctx.log("dedupe", "ok", candidates=len(ctx.candidates), new_drafts=len(ctx.merged), merged_into_existing=len(ctx.to_existing))


def step_recheck(ctx: Context) -> None:
    cutoff = ctx.now() - timedelta(days=config.RECHECK_DAYS)
    recent = [s for s in content.load_sightings(ctx.root) if _parse_iso(s.matched_at) >= cutoff]
    if not recent:
        ctx.log("recheck", "ok", checked=0, dropped=0)
        return
    try:
        present = ctx.reddit.info([s.fullname for s in recent])
    except (RedditRateLimited, RedditUnavailable) as e:
        ctx.record.recheck_skipped = 1
        ctx.log("recheck", "skipped", error=type(e).__name__)
        return
    to_drop = [s.fullname for s in recent if not present.get(s.fullname, False)]
    # A short or empty /api/info answer must not read as "everything was deleted".
    too_many = len(recent) >= config.RECHECK_RATIO_MIN_SAMPLE and len(to_drop) > config.RECHECK_MAX_DROP_RATIO * len(recent)
    if len(present) < len(recent) or too_many:
        ctx.record.recheck_skipped = 1
        ctx.log("recheck", "skipped", reason="implausible answer", answered=len(present), asked=len(recent), would_drop=len(to_drop))
        return
    ctx.to_drop = to_drop
    ctx.record.recheck_dropped = len(ctx.to_drop)
    ctx.log("recheck", "ok", checked=len(recent), dropped=len(ctx.to_drop))


def step_write(ctx: Context) -> None:
    if ctx.dry_run:
        ctx.log("write", "dry-run", sightings=len(ctx.sightings), drafts=len(ctx.merged), drop=len(ctx.to_drop))
        return
    ctx.status_snapshot = ctx.status.model_copy(deep=True)
    for s in ctx.sightings:
        content.save_sighting(ctx.root, s)
    today = ctx.date
    existing = {d.slug: d for d in content.load_drafts(ctx.root)}
    for cand in ctx.merged:
        slug = slugify(cand.text)
        links = _dedupe([u.permalink for u in cand.units])
        if slug in existing:
            d = _add_sightings(existing[slug], links)
        else:
            d = Draft(slug=slug, text=cand.text, first_seen=today, sightings_count=len(links), links=links)
        content.save_draft(ctx.root, d)
    for slug, units in ctx.to_existing.items():
        d = existing.get(slug)
        if d is None:
            continue
        content.save_draft(ctx.root, _add_sightings(d, [u.permalink for u in units]))
    if ctx.to_drop:
        content.drop_sightings(ctx.root, ctx.to_drop)
    ctx.status.carried = _dedupe(ctx.carried)
    # The watermark never moves backwards: a carried-only run processes old units.
    if ctx.new_watermark and (ctx.status.watermark is None or ctx.new_watermark > ctx.status.watermark):
        ctx.status.watermark = ctx.new_watermark
    ctx.record.outcome = "degraded" if ctx.status.degraded else "success"
    ctx.status.last_success = _iso(ctx.now())
    ctx.status.errors = []
    _finish_status(ctx)
    ctx.log("write", "ok", sightings=len(ctx.sightings), drafts=len(ctx.merged), dropped=len(ctx.to_drop), carried=len(ctx.status.carried))


def step_validate(ctx: Context) -> None:
    if ctx.dry_run:
        return
    problems = content.validate_tree(ctx.root)
    if problems:
        raise ContentInvalid("; ".join(problems[:5]))
    ctx.log("validate", "ok")


def step_commit(ctx: Context) -> None:
    if ctx.dry_run:
        ctx.log("commit", "dry-run")
        return
    msg = f"Referee: {ctx.date} {ctx.slot}: {ctx.record.matched} matched, {ctx.record.drafted} drafted, {ctx.record.carried} carried"
    committed = ctx.gitops.commit_all(msg)
    ctx.log("commit", "ok" if committed else "nothing-to-commit")


STEPS = [
    ("branch", step_branch),
    ("preflight", step_preflight),
    ("fetch", step_fetch),
    ("map", step_map),
    ("dedupe", step_dedupe),
    ("recheck", step_recheck),
    ("write", step_write),
    ("validate", step_validate),
    ("commit", step_commit),
]


def _add_sightings(d: Draft, permalinks: list) -> Draft:
    """Count only links the draft has not seen; re-processing a comment never inflates sightings_count."""
    new_links = [p for p in _dedupe(permalinks) if p not in d.links]
    if not new_links:
        return d
    # Every counted link is kept (the model allows many); what a page shows is the template's business.
    return d.model_copy(update={"sightings_count": d.sightings_count + len(new_links), "links": d.links + new_links})


def _dedupe(items: list) -> list:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _finish_status(ctx: Context) -> None:
    ctx.record.finished_at = _iso(ctx.now())
    ctx.record.duration_ms = int((_parse_iso(ctx.record.finished_at) - _parse_iso(ctx.record.started_at)).total_seconds() * 1000)
    # One record per run: a failure after write replaces the record the write step added.
    others = [r for r in ctx.status.runs if r.run_id != ctx.record.run_id]
    ctx.status.runs = (others + [ctx.record])[-config.RUNS_KEPT :]
    content.save_status(ctx.root, ctx.status)


def prepare(ctx: Context) -> int:
    ctx.record = RunRecord(run_id=uuid.uuid4().hex[:12], started_at=_iso(ctx.now()), outcome="failed")
    step_name = "start"
    try:
        for step_name, fn in STEPS:
            ctx.status.last_step = step_name
            fn(ctx)
            if ctx.exit_code is not None:
                return ctx.exit_code
        return 0
    except Exception as e:  # noqa: BLE001 - the one top-level handler
        ctx.record.outcome = "failed"
        # Class and step only: exception messages can carry comment text, and status.json is public.
        err = f"{type(e).__name__}@{step_name}" + (f" unit={ctx.current_unit}" if ctx.current_unit else "")
        ctx.record.errors.append(err)
        ctx.log(step_name, "failed", error=type(e).__name__)
        if not ctx.dry_run:
            try:
                if step_name in ("write", "validate", "commit"):
                    ctx.gitops.discard_content()
                    if ctx.status_snapshot is not None:
                        ctx.status = ctx.status_snapshot  # watermark, carried and last_success as before the write
                ctx.status.errors = [err]
                ctx.status.last_step = step_name
                if ctx.branch_ready:
                    _finish_status(ctx)
                    ctx.gitops.commit_all(f"Referee: {ctx.date} {ctx.slot} failed at {step_name}")
                else:
                    ctx.log(step_name, "status-not-committed", reason="bot branch not created")
            except Exception as inner:  # noqa: BLE001
                ctx.log(step_name, "status-not-saved", error=type(inner).__name__)
        raise


def publish(root: Path, gitops: Any, date: str, log_out: Callable[[str], None] = print, slot: str = "morning") -> int:
    status = content.load_status(root)
    branch = bot_branch(date, slot)
    if not gitops.has_unpushed_commits():
        log_out(json.dumps({"step": "publish", "outcome": "nothing-to-publish", "branch": branch, "slot": slot}))
        return 0
    last = status.runs[-1] if status.runs else None
    summary = f"{last.outcome}: {last.matched} matched, {last.drafted} drafted, {last.carried} carried, {last.recheck_dropped} dropped" if last else "no run record"
    title = f"Referee: {date} ({last.outcome if last else 'status'})"
    body = f"Automated daily run.\n\n{summary}\n\nErrors: {', '.join(status.errors) or 'none'}\n\nThe bot never changes a locked ruling; CI enforces it."
    url = gitops.push_and_open_pr(branch, title, body)
    log_out(json.dumps({"step": "publish", "outcome": "ok", "branch": branch, "slot": slot, "pr": url}))
    return 0


# --------------------------------------------------------------------------- CLI


def _build_ctx(args: argparse.Namespace) -> Context:
    from .gitops import GitOps, subprocess_runner
    from .mapper import Mapper
    from .reddit import RedditClient

    root = Path(args.root).resolve()
    claims = content.load_claims(root)
    client = None
    if not args.dry_run or os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic()
    mapper = Mapper(client, claims)
    return Context(root=root, slot=args.slot, reddit=RedditClient(), mapper=mapper, gitops=GitOps(subprocess_runner(str(root))), env=dict(os.environ), dry_run=args.dry_run, since=args.since, only=args.only)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m referee.run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--root", default=".")
    p.add_argument("--slot", choices=("morning", "noon"), default="morning")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--since", help="override the watermark, ISO like 2026-10-24T10:00:00Z")
    p.add_argument("--only", help="process one fullname only")
    q = sub.add_parser("publish")
    q.add_argument("--root", default=".")
    q.add_argument("--slot", choices=("morning", "noon"), default="morning", help="which scheduled slot this is; selects the bot/<date>-<slot> branch")
    q.add_argument("--date", default=_utcnow().strftime("%Y-%m-%d"))
    args = ap.parse_args(argv)
    if args.cmd == "prepare":
        ctx = _build_ctx(args)
        return prepare(ctx)
    if args.cmd == "publish":
        root = Path(args.root).resolve()
        return publish(root, _gitops_factory(root), args.date, slot=args.slot)
    return 2


def _gitops_factory(root: Path) -> Any:
    """Indirection so the CLI test can swap in a fake."""
    from .gitops import GitOps, subprocess_runner

    return GitOps(subprocess_runner(str(root)))


if __name__ == "__main__":
    raise SystemExit(main())
