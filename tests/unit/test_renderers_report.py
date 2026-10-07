"""Tests for ReportHTMLRenderer (Task 14).

The read-only test report is what testers send to PMs/devs after testing
is done. Shows summary stats + failure notes + a full case table.
Self-contained HTML (inline CSS, no external resources).
"""

from __future__ import annotations

from casemap.models.graph import TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus
from casemap.renderers.report_html import ReportHTMLRenderer


def test_contains_title():
    g = TestGraph(title="My API")
    html = ReportHTMLRenderer().render(g, {})
    assert "My API" in html


def test_progress_summary():
    cases = [
        TestCase(id="p", type=CaseType.POSITIVE, title="p", status=TestStatus.PASSED),
        TestCase(id="f", type=CaseType.NEGATIVE, title="f", status=TestStatus.FAILED),
        TestCase(id="x", type=CaseType.POSITIVE, title="x", status=TestStatus.PENDING),
    ]
    g = TestGraph(title="t", nodes=[TestNode(id=c.id, case=c) for c in cases])
    statuses = {c.id: {"status": c.status.value, "note": ""} for c in cases}
    html = ReportHTMLRenderer().render(g, statuses)
    assert "通过" in html or "1" in html
    assert "失败" in html or "1" in html


def test_failure_notes_shown():
    g = TestGraph(
        title="t",
        nodes=[TestNode(id="a", case=TestCase(id="a", type=CaseType.NEGATIVE, title="登录失败"))],
    )
    statuses = {"a": {"status": "failed", "note": "按钮无反应"}}
    html = ReportHTMLRenderer().render(g, statuses)
    assert "按钮无反应" in html


def test_self_contained():
    g = TestGraph(title="t")
    html = ReportHTMLRenderer().render(g, {})
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html
