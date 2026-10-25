"""One-off: draft content/questions and content/claims from the Oct 21 review's build.py.

Decision D29: records are paraphrases (no usernames, no verbatim quotes), with
sources extracted from the ruling's reasoning and confidence inherited from the
question until a per-claim value is set. Alex reviews every record in one PR.

Usage:
    python scripts/draft_claims.py --build /path/to/build.py --root . \
        --paraphrases data/paraphrases.json

Claims are numbered per question: the original post's own lines first, then the
commenter claims in build.py order. The paraphrase file maps claim id to
{"text": ..., "side": optional override}. Ids without a paraphrase are written
with a placeholder and listed in data/paraphrase-input.json for authoring.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from referee.content import Claim, Question, Side, Verdict, find_usernames, save_claim, save_question  # noqa: E402
from referee.content import scrub_usernames as _scrub  # noqa: E402

THREAD_URL = "https://www.reddit.com/r/DebateAChristian/comments/1vzrkx7/"


def load_questions_from_build(build_py: Path) -> list[dict]:
    src = build_py.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(src) if l.startswith("QUESTIONS = ["))
    end = next(i for i, l in enumerate(src) if l.startswith("INDEX = ["))
    ns: dict = {}
    exec("\n".join(src[start:end]), ns)  # noqa: S102 - our own file, data only
    return ns["QUESTIONS"]


def plain(s: str | None) -> str:
    """HTML fragment -> plain text with paragraph breaks preserved."""
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace(" ", " ")
    return re.sub(r"[ \t]+", " ", s).strip()


def scrub_usernames(text: str) -> str:
    """Decision D15: no usernames in content. Replace mentions with a neutral phrase."""
    text = re.sub(r"\(u/[A-Za-z0-9_-]{2,} went on to", "(One commenter went on to", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![A-Za-z0-9_])/?u/[A-Za-z0-9_-]{2,}'s\b", "another commenter's", text, flags=re.IGNORECASE)
    text = _scrub(text)
    text = re.sub(r"(^|[.!?]\s+|\(\s*)another commenter", lambda m: m.group(1) + "Another commenter", text)
    return text


# Lookbehind keeps URL paths like "nd.edu/news" out: a handle mention starts at a word boundary.
HANDLE_IN_BUILD_RE = re.compile(r"(?<![A-Za-z0-9_])u/([A-Za-z0-9_-]{3,})", re.IGNORECASE)


def handles_from_build(build_src: str) -> set[str]:
    """Every handle named in build.py's `who` fields (the raw source text is enough)."""
    return set(HANDLE_IN_BUILD_RE.findall(build_src))


def scan_content_for_handles(root: Path, handles: set[str]) -> dict[str, list[str]]:
    """Files under content/ that mention a known handle even without the u/ prefix."""
    hits: dict[str, list[str]] = {}
    for p in sorted((root / "content").rglob("*")):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        found = [h for h in sorted(handles) if re.search(r"(?<![A-Za-z0-9_])" + re.escape(h) + r"(?![A-Za-z0-9_])", text, re.IGNORECASE)]
        found += find_usernames(text)
        if found:
            hits[str(p.relative_to(root))] = found
    return hits


def side_for(who: str) -> Side:
    w = who.lower()
    if "christian" in w and "ex-christian" not in w.replace("agnostic christian", ""):
        return Side.THEIST
    if "muslim" in w:
        return Side.THEIST
    if any(k in w for k in ("atheist", "agnostic", "skeptic", "ignostic")):
        return Side.SKEPTIC
    return Side.UNSTATED


SOURCE_PATTERNS = [
    re.compile(r"<em>([^<]{4,120})</em>(?:,|\s)*\((\d{4})\)"),
    re.compile(r"([A-Z][\w&;.'’\- ]{2,60}?)\s*\((\d{4})\)"),
    re.compile(r"(arXiv:\d{4}\.\d{4,5})"),
    re.compile(r"\b((?:[123] )?(?:Cor(?:inthians)?|Mark|Matthew|Luke|John|Acts|Romans|Galatians|Thess(?:alonians)?)\s\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?)"),
]


def extract_sources(why_html: str) -> list[str]:
    found: list[str] = []
    for rx in SOURCE_PATTERNS:
        for m in rx.finditer(why_html):
            if len(m.groups()) == 2:
                s = f"{plain(m.group(1))} ({m.group(2)})"
            else:
                s = plain(m.group(1))
            s = s.strip(" ,;")
            if s and s not in found:
                found.append(s)
    return found[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True, type=Path)
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--paraphrases", type=Path, default=Path("data/paraphrases.json"))
    args = ap.parse_args()

    paraphrases: dict[str, dict] = {}
    if args.paraphrases.exists():
        paraphrases = json.loads(args.paraphrases.read_text(encoding="utf-8"))

    missing: dict[str, dict] = {}
    n_claims = 0
    for d in load_questions_from_build(args.build):
        qid = f"q{d['n']:02d}"
        q = Question(
            id=qid,
            n=d["n"],
            title=plain(d["title"]),
            confidence=d["conf"],
            short=plain(d["short"]),
            verdict=plain(d.get("verdict")) or plain(d["short"]),
            reply=plain(d["reply"]) if d.get("reply") else None,
            thread_url=THREAD_URL,
            body=plain(d.get("intro", "")),
        )
        save_question(args.root, q)

        entries: list[tuple[str, str, Verdict, int | None, str, Side]] = []
        for text, verdict in d.get("post", []):
            entries.append((text, text, Verdict(verdict), None, "This is a line from the original post, graded by the same rubric as the replies.", Side.THEIST))
        for who, quote, verdict, strength, why in d["rulings"]:
            entries.append((who, quote, Verdict(verdict), strength, why, side_for(who)))

        for i, (who, quote, verdict, strength, why_html, side) in enumerate(entries, 1):
            cid = f"{qid}-c{i:02d}"
            para = paraphrases.get(cid, {})
            text = para.get("text")
            if not text:
                text = "PARAPHRASE PENDING: see data/paraphrase-input.json"
                missing[cid] = {"who": who, "quote": plain(quote), "verdict": verdict.value}
            if para.get("side"):
                side = Side(para["side"])
            c = Claim(
                id=cid,
                question=qid,
                text=text,
                side=side,
                verdict=verdict,
                strength=strength,
                why=scrub_usernames(plain(why_html)),
                sources=extract_sources(why_html),
                confidence=d["conf"],
            )
            save_claim(args.root, c)
            n_claims += 1

    hits = scan_content_for_handles(args.root, handles_from_build(args.build.read_text(encoding="utf-8")))
    for path, found in hits.items():
        print(f"handle in content: {path}: {', '.join(found)}", file=sys.stderr)

    if missing:
        out = args.root / "data" / "paraphrase-input.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(missing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{len(missing)} claims need a paraphrase: {out}", file=sys.stderr)
    print(f"wrote {n_claims} claims")
    return 1 if (missing or hits) else 0


if __name__ == "__main__":
    raise SystemExit(main())
