"""Tests for JSONRenderer (Task 12)."""

from __future__ import annotations

import json

import pytest

from casemap._internal.exceptions import RenderError
from casemap.models.graph import Edge, TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus, TestStep
from casemap.renderers.json_export import JSONRenderer


def test_round_trip():
    g = TestGraph(
        title="x",
        nodes=[
            TestNode(
                id="a",
                case=TestCase(
                    id="a",
                    type=CaseType.POSITIVE,
                    title="t",
                    status=TestStatus.PASSED,
                    failure_note="",
                ),
            )
        ],
        edges=[Edge(source="a", target="a")],
        metadata={"k": "v"},
    )
    raw = JSONRenderer().render(g)
    data = json.loads(raw)
    assert data["version"] == 1
    assert data["graph"]["title"] == "x"
    g2 = JSONRenderer().parse(raw)
    assert g2.title == "x"
    assert g2.nodes[0].case.status == TestStatus.PASSED


def test_parse_invalid_raises():
    with pytest.raises(RenderError):
        JSONRenderer().parse("not json")


def test_version_field_present():
    """Contract: every emitted JSON must carry a top-level `version`."""
    g = TestGraph(title="empty")
    data = json.loads(JSONRenderer().render(g))
    assert data["version"] == 1


def test_round_trip_preserves_edges_and_metadata():
    g = TestGraph(
        title="x",
        nodes=[TestNode(id="a", case=TestCase(id="a", type=CaseType.POSITIVE, title="a"))],
        edges=[Edge(source="a", target="a", label="loop")],
        metadata={"owner": "qa", "sprint": "s1"},
    )
    g2 = JSONRenderer().parse(JSONRenderer().render(g))
    assert g2.metadata == {"owner": "qa", "sprint": "s1"}
    assert len(g2.edges) == 1
    assert g2.edges[0].label == "loop"
    assert g2.edges[0].source == "a"
    assert g2.edges[0].target == "a"


def test_round_trip_preserves_full_case_fields():
    """Steps + tags + description + endpoint_ref must survive parse."""
    case = TestCase(
        id="x",
        type=CaseType.SECURITY,
        title="注入测试",
        description="SQL 注入防护",
        steps=[
            TestStep(order=1, action="发送 payload", expected="attempt 1"),
            TestStep(order=2, action="验证响应", expected="attempt 2"),
        ],
        endpoint_ref="POST /api/login",
        tags=["auth", "critical"],
        status=TestStatus.FAILED,
        failure_note="服务端未拦截 union",
    )
    g = TestGraph(title="t", nodes=[TestNode(id="x", case=case)])
    g2 = JSONRenderer().parse(JSONRenderer().render(g))
    c2 = g2.nodes[0].case
    assert c2.id == "x"
    assert c2.type == CaseType.SECURITY
    assert c2.title == "注入测试"
    assert c2.description == "SQL 注入防护"
    assert c2.endpoint_ref == "POST /api/login"
    assert c2.tags == ["auth", "critical"]
    assert c2.status == TestStatus.FAILED
    assert c2.failure_note == "服务端未拦截 union"
    assert [s.model_dump() for s in c2.steps] == [
        {"order": 1, "action": "发送 payload", "expected": "attempt 1"},
        {"order": 2, "action": "验证响应", "expected": "attempt 2"},
    ]


def test_round_trip_empty_graph():
    g = TestGraph(title="empty")
    g2 = JSONRenderer().parse(JSONRenderer().render(g))
    assert g2.title == "empty"
    assert g2.nodes == []
    assert g2.edges == []
    assert g2.metadata == {}
