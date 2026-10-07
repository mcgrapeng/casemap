"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def logger():
    """Provide a casemap logger for tests."""
    from casemap._internal.logger import get_logger
    return get_logger("tests")
