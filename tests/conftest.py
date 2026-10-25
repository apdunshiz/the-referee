from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pytest

from referee import content
from referee.content import Claim, Question, Side, Verdict


@dataclass
class FakeResponse:
    status_code: int = 200
    json_data: Any = None
    headers: dict = field(default_factory=dict)
    text: str = ""

    def json(self):
        if self.json_data is None:
            raise ValueError("no json")
        return self.json_data


class FakeSession:
    """Returns queued responses in order; records every call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def _next(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if not self.responses:
            raise AssertionError(f"no fake response left for {method} {url}")
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, **kw):
        return self._next("POST", url, **kw)

    def get(self, url, **kw):
        return self._next("GET", url, **kw)


def token_ok():
    return FakeResponse(200, {"access_token": "secret-token", "token_type": "bearer"})


def make_claims():
    return [
        Claim(id="q01-c01", question="q01", text="The universe had a beginning.", side=Side.THEIST, verdict=Verdict.OPEN, why="A beginning is a live position but not established.", confidence=90),
        Claim(id="q01-c02", question="q01", text="Energy cannot be created or destroyed, so there was no beginning.", side=Side.SKEPTIC, verdict=Verdict.FALSE, strength=2, why="Energy conservation describes what happens within time.", confidence=90),
        Claim(id="q09-c07", question="q09", text="A Columbine martyr story became accepted within a week, so legends can form almost instantly.", side=Side.SKEPTIC, verdict=Verdict.MOSTLY_TRUE, strength=8, why="The story spread within days.", confidence=85),
    ]


@pytest.fixture
def claims():
    return make_claims()


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    content.save_question(tmp_path, Question(id="q01", n=1, title="Did the universe begin?", confidence=90, short="Open.", verdict="Open question."))
    content.save_question(tmp_path, Question(id="q09", n=9, title="Hallucinations and fast legends", confidence=85, short="Mixed.", verdict="Mixed."))
    for c in make_claims():
        content.save_claim(tmp_path, c)
    (tmp_path / "content" / "sightings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "content" / "claims" / "new").mkdir(parents=True, exist_ok=True)
    return tmp_path
