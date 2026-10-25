"""Reddit Data API client for the bot (official OAuth script app, read-only).

Everything network-related for Reddit lives here. The HTTP session is injected so
tests use a fake; the sleep function is injected so backoff is testable.

Typed failures (see the plan's Error & Rescue Registry):
    RedditAuthError      401/403 on the token endpoint, or 401 later
    RedditUnavailable    5xx or timeouts after three retries
    RedditRateLimited    429 that persists after one sleep-until-reset
    RedditForbidden      403 on a listing (banned, private)
    RedditParseError     response that is not the JSON shape we expect
    RedditGone           404 for a post
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

import requests

from . import config

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
MORECHILDREN_BATCH = 100
INFO_BATCH = 100
MAX_MORECHILDREN_ROUNDS = 20


class RedditError(Exception):
    pass


class RedditAuthError(RedditError):
    pass


class RedditUnavailable(RedditError):
    pass


class RedditRateLimited(RedditError):
    def __init__(self, reset_s: float):
        super().__init__(f"rate limited; reset in {reset_s:.0f}s")
        self.reset_s = reset_s


class RedditForbidden(RedditError):
    pass


class RedditParseError(RedditError):
    pass


class RedditGone(RedditError):
    pass


@dataclass
class Unit:
    """A post or comment that is a candidate for mapping."""

    fullname: str
    kind: str  # "post" | "comment"
    permalink: str
    text: str
    created_utc: float
    post_id: str
    truncated: bool = False


@dataclass
class Credentials:
    client_id: str
    client_secret: str
    username: str
    password: str

    @classmethod
    def from_env(cls) -> "Credentials":
        missing = [k for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD") if not os.environ.get(k)]
        if missing:
            raise RedditAuthError(f"missing environment variables: {', '.join(missing)}")
        return cls(os.environ["REDDIT_CLIENT_ID"], os.environ["REDDIT_CLIENT_SECRET"], os.environ["REDDIT_USERNAME"], os.environ["REDDIT_PASSWORD"])


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


class RedditClient:
    def __init__(
        self,
        creds: Optional[Credentials] = None,
        session: Optional[Any] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.time,
    ):
        self.creds = creds
        self.session = session or requests.Session()
        self.sleep = sleep
        self.now = now
        self._token: Optional[str] = None
        self.requests_made = 0

    # ------------------------------------------------------------------ auth

    @property
    def user_agent(self) -> str:
        return config.USER_AGENT.format(username=self.creds.username if self.creds else "anonymous")

    def get_token(self) -> str:
        if self.creds is None:
            self.creds = Credentials.from_env()
        last: Optional[Exception] = None
        for attempt, wait in enumerate((0,) + config.REDDIT_BACKOFF_S):
            if wait:
                self.sleep(wait)
            try:
                r = self.session.post(
                    TOKEN_URL,
                    data={"grant_type": "password", "username": self.creds.username, "password": self.creds.password},
                    auth=(self.creds.client_id, self.creds.client_secret),
                    headers={"User-Agent": self.user_agent},
                    timeout=config.REDDIT_TIMEOUT_S,
                )
            except (requests.Timeout, requests.ConnectionError) as e:
                last = e
                continue
            self.requests_made += 1
            if r.status_code in (401, 403):
                raise RedditAuthError(f"token endpoint returned {r.status_code}")
            if r.status_code >= 500:
                last = RedditUnavailable(f"token endpoint returned {r.status_code}")
                continue
            try:
                body = r.json()
            except ValueError as e:
                raise RedditParseError("token response is not JSON") from e
            if "access_token" not in body:
                # Reddit answers 200 with {"error": "invalid_grant"} for bad credentials or 2FA.
                raise RedditAuthError(f"token response: {body.get('error', 'no access_token')}")
            self._token = body["access_token"]
            return self._token
        raise RedditUnavailable(f"token endpoint unavailable after retries: {last}")

    def _headers(self) -> dict:
        if not self._token:
            self.get_token()
        return {"Authorization": f"bearer {self._token}", "User-Agent": self.user_agent}

    # ------------------------------------------------------------------ transport

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """GET with rate-limit handling and retries. Returns parsed JSON."""
        url = API + path
        slept_for_reset = False
        last: Optional[Exception] = None
        attempt = 0
        while attempt <= len(config.REDDIT_BACKOFF_S):
            try:
                r = self.session.get(url, params=params or {}, headers=self._headers(), timeout=config.REDDIT_TIMEOUT_S)
            except (requests.Timeout, requests.ConnectionError) as e:
                last = e
                if attempt < len(config.REDDIT_BACKOFF_S):
                    self.sleep(config.REDDIT_BACKOFF_S[attempt])
                attempt += 1
                continue
            self.requests_made += 1
            status = r.status_code
            if status == 429:
                reset = min(_f(r.headers.get("X-Ratelimit-Reset"), 60.0), config.REDDIT_RATELIMIT_SLEEP_CAP_S)
                if slept_for_reset:
                    raise RedditRateLimited(reset)
                self.sleep(reset)
                slept_for_reset = True
                continue
            if status == 401:
                raise RedditAuthError("401 on API call")
            if status == 403:
                raise RedditForbidden(f"403 on {path}")
            if status == 404:
                raise RedditGone(f"404 on {path}")
            if status >= 500:
                last = RedditUnavailable(f"{status} on {path}")
                if attempt < len(config.REDDIT_BACKOFF_S):
                    self.sleep(config.REDDIT_BACKOFF_S[attempt])
                attempt += 1
                continue
            try:
                body = r.json()
            except ValueError as e:
                raise RedditParseError(f"non-JSON body on {path}: {str(r.text)[:200]!r}") from e
            # Proactive pause when the window is spent.
            remaining = _f(r.headers.get("X-Ratelimit-Remaining"), 1.0)
            if remaining < 1:
                self.sleep(min(_f(r.headers.get("X-Ratelimit-Reset"), 1.0), config.REDDIT_RATELIMIT_SLEEP_CAP_S))
            return body
        raise RedditUnavailable(f"{path} unavailable after retries: {last}")

    # ------------------------------------------------------------------ listings

    def fetch_window(self, days: int = config.WINDOW_DAYS) -> list[dict]:
        """Posts from /new, newest first, until older than the window. Returns post `data` dicts."""
        cutoff = self.now() - days * 86400
        posts: list[dict] = []
        after: Optional[str] = None
        for _ in range(50):  # hard cap: 5,000 posts
            params = {"limit": 100}
            if after:
                params["after"] = after
            body = self._get(f"/r/{config.SUBREDDIT}/new", params)
            try:
                children = body["data"]["children"]
                after = body["data"].get("after")
            except (KeyError, TypeError) as e:
                raise RedditParseError("listing shape") from e
            done = False
            for ch in children:
                data = ch.get("data", {})
                if _f(data.get("created_utc")) < cutoff:
                    done = True
                    break
                posts.append(data)
            if done or not after or not children:
                break
        return posts

    def fetch_comments(self, post_id: str) -> list[dict]:
        """Every comment `data` dict of a post, with `more` stubs expanded."""
        body = self._get(f"/comments/{post_id}", {"limit": 500, "depth": 10, "sort": "new"})
        try:
            listing = body[1]["data"]["children"]
        except (KeyError, TypeError, IndexError) as e:
            raise RedditParseError("comments shape") from e
        comments: list[dict] = []
        stubs: list[str] = []
        self._walk(listing, comments, stubs)
        rounds = 0
        while stubs and rounds < MAX_MORECHILDREN_ROUNDS:
            rounds += 1
            batch, stubs = stubs[:MORECHILDREN_BATCH], stubs[MORECHILDREN_BATCH:]
            more = self._get("/api/morechildren", {"link_id": f"t3_{post_id}", "children": ",".join(batch), "api_type": "json", "limit_children": "false"})
            try:
                things = more["json"]["data"]["things"]
            except (KeyError, TypeError) as e:
                raise RedditParseError("morechildren shape") from e
            self._walk(things, comments, stubs)
        return comments

    def _walk(self, children: Iterable[dict], out: list[dict], stubs: list[str]) -> None:
        for ch in children:
            kind = ch.get("kind")
            data = ch.get("data", {})
            if kind == "t1":
                out.append(data)
                replies = data.get("replies")
                if isinstance(replies, dict):
                    self._walk(replies.get("data", {}).get("children", []), out, stubs)
            elif kind == "more":
                stubs.extend(c for c in data.get("children", []) if re.match(r"^[a-z0-9]+$", str(c)))

    def info(self, fullnames: Iterable[str]) -> dict[str, bool]:
        """fullname -> True when the thing still exists with a body. Absent or removed -> False."""
        names = [n for n in fullnames]
        present: dict[str, bool] = {n: False for n in names}
        for i in range(0, len(names), INFO_BATCH):
            batch = names[i : i + INFO_BATCH]
            body = self._get("/api/info", {"id": ",".join(batch)})
            try:
                children = body["data"]["children"]
            except (KeyError, TypeError) as e:
                raise RedditParseError("info shape") from e
            for ch in children:
                data = ch.get("data", {})
                name = data.get("name")
                if name not in present:
                    continue
                text = data.get("body") if ch.get("kind") == "t1" else data.get("selftext")
                removed = text in ("[removed]", "[deleted]") or data.get("removed_by_category") or data.get("author") == "[deleted]"
                present[name] = not removed
        return present


# ---------------------------------------------------------------------- units


def unit_from_post(data: dict) -> Optional[Unit]:
    title = normalize(data.get("title", ""))
    body = normalize(data.get("selftext", ""))
    if body in ("[removed]", "[deleted]"):
        return None
    text = (title + "\n\n" + body).strip()
    return _make_unit(data, "post", text, data.get("id", ""))


def unit_from_comment(data: dict) -> Optional[Unit]:
    body = normalize(data.get("body", ""))
    if body in ("[removed]", "[deleted]") or data.get("author") == "[deleted]":
        return None
    link_id = str(data.get("link_id", ""))
    return _make_unit(data, "comment", body.strip(), link_id.split("_", 1)[-1])


def _make_unit(data: dict, kind: str, text: str, post_id: str) -> Optional[Unit]:
    if len(text) < config.MIN_UNIT_CHARS:
        return None
    fullname = str(data.get("name", ""))
    if not re.match(r"^t[13]_[a-z0-9]+$", fullname):
        return None
    truncated = False
    if len(text) > config.MAX_UNIT_CHARS:
        text = text[: config.MAX_UNIT_CHARS]
        truncated = True
    permalink = str(data.get("permalink", ""))
    if not permalink.startswith("/r/"):
        return None
    return Unit(fullname=fullname, kind=kind, permalink=config.THREAD_HOST + permalink, text=text, created_utc=_f(data.get("created_utc")), post_id=post_id, truncated=truncated)


def units_from(posts: Iterable[dict], comments: Iterable[dict]) -> tuple[list[Unit], int]:
    """Build units; returns (units, malformed_or_short_count)."""
    units: list[Unit] = []
    dropped = 0
    for p in posts:
        u = unit_from_post(p)
        if u:
            units.append(u)
        else:
            dropped += 1
    for c in comments:
        u = unit_from_comment(c)
        if u:
            units.append(u)
        else:
            dropped += 1
    return units, dropped
