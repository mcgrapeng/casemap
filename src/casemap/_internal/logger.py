"""Structured logger for casemap (stdlib logging, no deps)."""

from __future__ import annotations

import logging
import os

_LOGGER_NAME = "casemap"


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger under the casemap namespace.

    Args:
        name: Optional sub-logger name (e.g. "parsers.openapi").
              Final logger will be "casemap.<name>" or just "casemap".
    """
    full_name = f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME
    logger = logging.getLogger(full_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
    level = os.environ.get("CASEMAP_LOG_LEVEL", "WARNING").upper()
    logger.setLevel(level)
    return logger
