from __future__ import annotations

import pytest

from casemap.models.graph import Edge, TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus


def _case(status: TestStatus = TestStatus.PENDING) -> TestCase:
    return TestCase(id="x", type=CaseType.POSITIVE, title="t", status=status)


class TestTestGraph:
    def test_empty(self):
        g = TestGraph(title="p")
        assert g.title == "p"
        assert g.nodes == []
        assert g.edges == []
        assert g.metadata == {}

    def test_progress_counts(self):
        cases = [
            TestCase(id=f"i{i}", type=CaseType.POSITIVE, title="t", status=s)
            for i, s in enumerate(
                [
                    TestStatus.PASSED,
                    TestStatus.PASSED,
                    TestStatus.FAILED,
                    TestStatus.PENDING,
                    TestStatus.PENDING,
                    TestStatus.PENDING,
                ]
            )
        ]
        nodes = [TestNode(id=c.id, case=c) for c in cases]
        g = TestGraph(title="p", nodes=nodes)
        progress = g.progress
        assert progress["total"] == 6
        assert progress["passed"] == 2
        assert progress["failed"] == 1
        assert progress["pending"] == 3
        assert progress["completion_pct"] == pytest.approx(33.33, rel=0.01)

    def test_serialize_roundtrip(self):
        g = TestGraph(
            title="x",
            nodes=[TestNode(id="a", case=_case())],
            edges=[Edge(source="a", target="a", label="loop")],
        )
        s = g.model_dump_json()
        g2 = TestGraph.model_validate_json(s)
        assert len(g2.nodes) == 1
        assert len(g2.edges) == 1
