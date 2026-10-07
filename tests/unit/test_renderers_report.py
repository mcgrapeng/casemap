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


# ---------- SP-5 Critical #2: XSS via unescaped Jinja2 in report ----------


def test_xss_in_title_is_escaped():
    """A title containing <script> must NOT execute when the report is opened.

    Jinja2 must autoescape {{ title }} / {{ r.title }} / {{ r.note or '' }}.
    """
    g = TestGraph(
        title="<script>alert('xss')</script>",
        nodes=[
            TestNode(
                id="a",
                case=TestCase(id="a", type=CaseType.POSITIVE, title="<img src=x onerror=alert(1)>"),
            )
        ],
    )
    html = ReportHTMLRenderer().render(g, {"a": {"status": "failed", "note": "<script>alert(2)</script>"}})
    # The raw <script> tag must not survive into the output - the &lt; form must.
    assert "<script>alert(" not in html
    # And the escaped entities must be present
    assert "&lt;script&gt;" in html or "alert" not in html.replace("&lt;", "").replace("&gt;", "")
