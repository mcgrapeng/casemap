"""TestCase data models - the unified test case representation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CaseType(str, Enum):
    """Classification of a test case."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    EDGE = "edge"
    SECURITY = "security"


class TestStatus(str, Enum):
    """Lifecycle status of a test case (set/updated by human testers)."""

    __test__ = False  # pytest: do not collect this class as a test
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TestStep(BaseModel):
    """A single step in a test case (action + expected)."""

    __test__ = False  # pytest: do not collect this class as a test
    model_config = ConfigDict(extra="forbid")

    order: int
    action: str
    expected: str


class TestCase(BaseModel):
    """A unified test case."""

    __test__ = False  # pytest: do not collect this class as a test
    model_config = ConfigDict(extra="forbid")

    id: str
    type: CaseType
    title: str
    description: str = ""
    steps: list[TestStep] = Field(default_factory=list)
    endpoint_ref: str | None = None  # e.g. "POST /api/users"
    tags: list[str] = Field(default_factory=list)
    status: TestStatus = TestStatus.PENDING
    failure_note: str = ""


