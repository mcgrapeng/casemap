"""Parser protocol + registry for SP-4 (document parsing)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from casemap._internal.exceptions import ParseError
from casemap.models.endpoint import Endpoint

_MISSING: Any = object()


@runtime_checkable
class Parser(Protocol):
    """Implement this Protocol to add a new document format.

    Required attributes/methods:
        - name: short identifier (e.g. "openapi")
        - version: parser version string
        - can_parse(data): sniff if this parser handles the input
        - parse(data): convert input -> list[Endpoint]
    """

    name: str
    version: str

    def can_parse(self, data: dict[str, Any] | str | bytes) -> bool: ...
    def parse(self, data: dict[str, Any] | str | bytes) -> list[Endpoint]: ...


class ParserRegistry:
    """Global registry of available parsers.

    Thread-safety: not thread-safe (single-threaded CLI usage is the norm).
    """

    _parsers: list[Parser] = []

    @classmethod
    def register(cls, parser: Parser) -> None:
        # Replace if already registered (idempotent re-registration)
        cls._parsers = [p for p in cls._parsers if p.name != parser.name]
        cls._parsers.append(parser)

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._parsers = [p for p in cls._parsers if p.name != name]

    @classmethod
    def get(cls, name: str, *, default: Parser | None = _MISSING) -> Parser | None:
        for p in cls._parsers:
            if p.name == name:
                return p
        if default is not _MISSING:
            return default
        raise KeyError(f"Parser not registered: {name!r}")

    @classmethod
    def auto_detect(cls, data: dict[str, Any] | str | bytes) -> Parser | None:
        """Return first parser whose can_parse() returns True."""
        for p in cls._parsers:
            try:
                if p.can_parse(data):
                    return p
            except Exception:  # noqa: BLE001 - a bad parser must not break others
                continue
        return None

    @classmethod
    def all(cls) -> list[Parser]:
        """Return all registered parsers (defensive copy)."""
        return list(cls._parsers)

    @classmethod
    def parse_auto(cls, data: dict[str, Any] | str | bytes) -> list[Endpoint]:
        """Auto-detect parser and parse. Raises ParseError on failure."""
        parser = cls.auto_detect(data)
        if parser is None:
            raise ParseError(
                f"No parser matched the input. Registered parsers: {[p.name for p in cls.all()]}"
            )
        return parser.parse(data)
