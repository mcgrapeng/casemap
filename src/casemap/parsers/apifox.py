"""apifox export parser.

apifox exports OpenAPI 3.x with optional x-apifox-* extensions. We
delegate to the OpenAPI parser; the x-apifox marker lets apifox be
explicitly selected via ParserRegistry.get("apifox").
"""

from __future__ import annotations

from typing import Any

from casemap._internal.logger import get_logger
from casemap.models.endpoint import Endpoint
from casemap.parsers.base import ParserRegistry
from casemap.parsers.openapi import OpenAPIParser

_log = get_logger("parsers.apifox")


def _has_apifox_marker(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if "x-apifox" in data:
        return True
    return any(isinstance(v, dict) and "x-apifox" in v for v in data.values())


class ApifoxParser:
    name = "apifox"
    version = "1.0"
    _delegate = OpenAPIParser()

    def can_parse(self, data: dict[str, Any] | str | bytes) -> bool:
        # Either has apifox marker, or is plain openapi (apifox IS openapi)
        return _has_apifox_marker(data) or self._delegate.can_parse(data)

    def parse(self, data: dict[str, Any] | str | bytes) -> list[Endpoint]:
        _log.debug("apifox parser delegating to openapi parser")
        return self._delegate.parse(data)


# Self-register LAST so OpenAPI gets priority in auto_detect.
# parsers/__init__.py loads openapi → postman → apifox in that order;
# auto_detect returns first match, so when an apifox-shaped openapi spec
# (no x-apifox marker) is loaded, openapi wins. The apifox parser is for
# explicit selection via ParserRegistry.get("apifox").
ParserRegistry.register(ApifoxParser())
