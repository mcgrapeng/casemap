from __future__ import annotations

from casemap.models.endpoint import Endpoint, HttpMethod
from casemap.parsers.base import Parser, ParserRegistry


class FakeParser:
    name = "fake"
    version = "1.0"

    def can_parse(self, data):
        return data == "fake"

    def parse(self, data):
        return [Endpoint(path="/x", method=HttpMethod.GET)]


class AnotherParser:
    name = "another"
    version = "1.0"

    def can_parse(self, data):
        return False

    def parse(self, data):
        return []


def setup_function(function):
    ParserRegistry._parsers.clear()


def test_register_and_get():
    ParserRegistry.register(FakeParser())
    assert ParserRegistry.get("fake").name == "fake"


def test_get_missing_raises():
    import pytest

    with pytest.raises(KeyError):
        ParserRegistry.get("nonexistent")


def test_auto_detect_first_match():
    ParserRegistry.register(FakeParser())
    ParserRegistry.register(AnotherParser())
    p = ParserRegistry.auto_detect("fake")
    assert p.name == "fake"


def test_auto_detect_returns_none_when_nothing_matches():
    ParserRegistry.register(AnotherParser())
    assert ParserRegistry.auto_detect("nope") is None


def test_unregister():
    ParserRegistry.register(FakeParser())
    ParserRegistry.unregister("fake")
    assert ParserRegistry.get("fake", default=None) is None  # type: ignore[arg-type]


def test_all_returns_registered():
    ParserRegistry.register(FakeParser())
    ParserRegistry.register(AnotherParser())
    names = {p.name for p in ParserRegistry.all()}
    assert names == {"fake", "another"}


def test_protocol_structural():
    # The Parser Protocol must be satisfied structurally (no isinstance check)
    p = FakeParser()
    assert isinstance(p, Parser) or hasattr(p, "can_parse") and hasattr(p, "parse")
