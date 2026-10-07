"""Document parsers (SP-4)."""

from __future__ import annotations

import contextlib

from casemap.parsers.base import Parser, ParserRegistry

# Side-effect imports trigger each parser's self-registration.
# These modules are created in Tasks 6-7; suppress ImportError so Task 5
# stays self-contained if they don't exist yet.
for _name in ("openapi", "postman", "apifox"):
    with contextlib.suppress(ModuleNotFoundError):
        __import__(f"casemap.parsers.{_name}")


def all_parsers() -> list[Parser]:
    """Return all registered parsers (for `casemap parsers list`)."""
    return ParserRegistry.all()


__all__ = ["Parser", "ParserRegistry", "all_parsers"]
