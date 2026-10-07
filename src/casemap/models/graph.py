"""TestGraph - the full graph of test cases + edges + metadata."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from casemap.models.testcase import TestCase, TestStatus


class TestNode(BaseModel):
    """A node in the test graph (wraps a TestCase)."""

    __test__ = False  # pytest: do not collect this class as a test
    model_config = ConfigDict(extra="forbid")

    id: str
    case: TestCase


class Edge(BaseModel):
    """An edge between two test nodes (workflow dependency)."""

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    label: str = ""


class TestGraph(BaseModel):
    """The full graph (nodes = test cases, edges = workflow)."""

    __test__ = False  # pytest: do not collect this class as a test
    model_config = ConfigDict(extra="forbid")

    title: str
    nodes: list[TestNode] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def progress(self) -> dict[str, int | float]:
        """Aggregate status counts across all nodes.

        Returns dict with keys: total, pending, in_progress, passed,
        failed, blocked, skipped, completion_pct (0-100, 2 decimals).
        completion_pct = passed / total * 100.
        """
        counts: dict[str, int] = {s.value: 0 for s in TestStatus}
        for n in self.nodes:
            counts[n.case.status.value] += 1
        total = len(self.nodes)
        passed = counts[TestStatus.PASSED.value]
        pct = round(passed / total * 100, 2) if total > 0 else 0.0
        return {"total": total, **counts, "completion_pct": pct}


