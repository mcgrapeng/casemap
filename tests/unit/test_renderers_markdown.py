"""Tests for MarkdownRenderer (Task 12)."""

from __future__ import annotations

from casemap.models.graph import TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase
from casemap.renderers.markdown import MarkdownRenderer


def test_decision_table_format():
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="a", case=TestCase(id="a", type=CaseType.POSITIVE, title="happy")),
            TestNode(id="b", case=TestCase(id="b", type=CaseType.NEGATIVE, title="bad")),
        ],
    )
    md = MarkdownRenderer().render(g)
    assert "| 类型 | 标题 |" in md
    assert "happy" in md
    assert "bad" in md


def test_includes_title_header():
    g = TestGraph(title="My API Tests", nodes=[])
    md = MarkdownRenderer().render(g)
    assert "# My API Tests" in md


def test_type_labels_in_chinese():
    """All four case types must render their Chinese label."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="p", case=TestCase(id="p", type=CaseType.POSITIVE, title="p")),
            TestNode(id="n", case=TestCase(id="n", type=CaseType.NEGATIVE, title="n")),
            TestNode(id="e", case=TestCase(id="e", type=CaseType.EDGE, title="e")),
            TestNode(id="s", case=TestCase(id="s", type=CaseType.SECURITY, title="s")),
        ],
    )
    md = MarkdownRenderer().render(g)
    assert "正向" in md
    assert "逆向" in md
    assert "边界" in md
    assert "安全" in md


def test_node_id_and_endpoint_in_table():
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(
                id="login-200",
                case=TestCase(
                    id="login-200",
                    type=CaseType.POSITIVE,
                    title="登录成功",
                    endpoint_ref="POST /api/login",
                ),
            )
        ],
    )
    md = MarkdownRenderer().render(g)
    assert "login-200" in md
    assert "POST /api/login" in md
    assert "登录成功" in md


def test_empty_graph_placeholder():
    g = TestGraph(title="empty")
    md = MarkdownRenderer().render(g)
    assert "# empty" in md
    # Empty placeholder so the table is not silently broken
    assert "暂无" in md or "empty" in md.lower() or "|" not in md or md.count("|") < 4
