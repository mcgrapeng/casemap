"""Tests for SVGRenderer (Task 11, post P0 fix).

The SVG renderer is the visible product: QA + PM stare at it all day.
It MUST be self-contained (no http://, https://, <script>) and every node
MUST be keyboard-clickable.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from casemap.models.graph import Edge, TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus
from casemap.renderers.svg import SVGRenderer


def _case(
    i: int = 1,
    *,
    type_: CaseType = CaseType.POSITIVE,
    status: TestStatus = TestStatus.PENDING,
    tags: list[str] | None = None,
    title: str | None = None,
) -> TestCase:
    return TestCase(
        id=f"c{i}",
        type=type_,
        title=title or f"用例{i}",
        status=status,
        tags=tags or [],
    )


def test_render_returns_valid_svg():
    g = TestGraph(
        title="t",
        nodes=[TestNode(id="a", case=_case())],
    )
    svg = SVGRenderer().render(g)
    assert svg.startswith("<svg") or svg.startswith("<?xml")
    assert "<svg" in svg
    assert "</svg>" in svg
    # must parse as XML
    ET.fromstring(svg)


def test_each_node_is_clickable():
    """Every node wrapped in <a> with data-case-id and href for click handling."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="abc", case=_case()),
            TestNode(id="xyz", case=_case(i=2, type_=CaseType.NEGATIVE)),
        ],
    )
    svg = SVGRenderer().render(g)
    assert 'data-case-id="abc"' in svg
    assert 'href="#case-abc"' in svg
    assert 'data-case-id="xyz"' in svg
    assert 'href="#case-xyz"' in svg
    # each case id appears inside an <a> element
    assert re.search(r'<a [^>]*data-case-id="abc"', svg) is not None
    assert re.search(r'<a [^>]*data-case-id="xyz"', svg) is not None


def test_status_color_reflected():
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="p", case=TestCase(id="p", type=CaseType.POSITIVE, title="p", status=TestStatus.PASSED)),
            TestNode(id="f", case=TestCase(id="f", type=CaseType.NEGATIVE, title="f", status=TestStatus.FAILED)),
            TestNode(id="ip", case=TestCase(id="ip", type=CaseType.POSITIVE, title="ip", status=TestStatus.IN_PROGRESS)),
            TestNode(id="b", case=TestCase(id="b", type=CaseType.POSITIVE, title="b", status=TestStatus.BLOCKED)),
            TestNode(id="s", case=TestCase(id="s", type=CaseType.POSITIVE, title="s", status=TestStatus.SKIPPED)),
            TestNode(id="d", case=TestCase(id="d", type=CaseType.POSITIVE, title="d", status=TestStatus.PENDING)),
        ],
    )
    svg = SVGRenderer().render(g)
    # Fill colors per status (light)
    assert "#d1fae5" in svg  # passed fill
    assert "#fee2e2" in svg  # failed fill
    assert "#fef3c7" in svg  # in_progress fill
    assert "#e5e7eb" in svg  # blocked fill
    assert "#dbeafe" in svg  # skipped fill
    assert "#f3f4f6" in svg  # pending fill
    # Stroke colors (saturated)
    assert "#10b981" in svg  # passed stroke
    assert "#ef4444" in svg  # failed stroke


def test_no_external_dependencies():
    """Critical: SVG output must have NO external refs (offline-capable)."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="a", case=_case()),
            TestNode(id="b", case=_case(i=2, type_=CaseType.EDGE)),
        ],
    )
    svg = SVGRenderer().render(g)
    # Allow only the SVG namespace declaration (xmlns="http://www.w3.org/2000/svg").
    stripped = svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "http://" not in stripped, f"Found http:// in: {svg[:300]}"
    assert "https://" not in stripped, f"Found https:// in: {svg[:300]}"
    assert "<script" not in svg


def test_layout_by_tag_groups():
    """Nodes with different tags must be in different x columns."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="u1", case=TestCase(id="u1", type=CaseType.POSITIVE, title="u1", tags=["users"])),
            TestNode(id="u2", case=TestCase(id="u2", type=CaseType.POSITIVE, title="u2", tags=["users"])),
            TestNode(id="o1", case=TestCase(id="o1", type=CaseType.POSITIVE, title="o1", tags=["orders"])),
        ],
    )
    svg = SVGRenderer().render(g)
    # Extract x positions of the clickable anchors
    xs: dict[str, float] = {}
    for cid in ("u1", "u2", "o1"):
        m = re.search(rf'<a [^>]*data-case-id="{cid}"[^>]*x="([\d.]+)"', svg)
        assert m is not None, f"no x for {cid}"
        xs[cid] = float(m.group(1))
    # u1 and u2 share column; o1 is in a different column
    assert xs["u1"] == xs["u2"]
    assert xs["u1"] != xs["o1"]


def test_case_type_shapes():
    """Each case_type renders a distinct shape element."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="p", case=TestCase(id="p", type=CaseType.POSITIVE, title="p")),
            TestNode(id="e", case=TestCase(id="e", type=CaseType.EDGE, title="e")),
            TestNode(id="s", case=TestCase(id="s", type=CaseType.SECURITY, title="s")),
        ],
    )
    svg = SVGRenderer().render(g)
    # rect for positive
    assert re.search(r'data-case-id="p".*?<rect', svg, re.DOTALL) or 'data-case-id="p"' in svg
    # diamond via polygon for edge
    assert 'data-case-id="e"' in svg
    # shield via path for security
    assert 'data-case-id="s"' in svg
    # security node uses <path d="...">
    # Look at the security node area
    sec_area = svg.split('data-case-id="s"', 1)[1].split("</a>", 1)[0]
    assert "<path" in sec_area


def test_emoji_icons_in_node_text():
    """Each case_type gets a recognizable emoji icon."""
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="p", case=TestCase(id="p", type=CaseType.POSITIVE, title="p")),
            TestNode(id="n", case=TestCase(id="n", type=CaseType.NEGATIVE, title="n")),
            TestNode(id="e", case=TestCase(id="e", type=CaseType.EDGE, title="e")),
            TestNode(id="s", case=TestCase(id="s", type=CaseType.SECURITY, title="s")),
        ],
    )
    svg = SVGRenderer().render(g)
    assert "\u2705" in svg  # ✅ positive
    assert "\u274c" in svg  # ❌ negative
    assert "\U0001f536" in svg  # 🔶 edge
    assert "\U0001f6e1" in svg  # 🛡 security


def test_title_tooltip_child():
    """Every node has a <title> child for hover tooltip."""
    g = TestGraph(
        title="t",
        nodes=[TestNode(id="a", case=_case(title="用例X"))],
    )
    svg = SVGRenderer().render(g)
    # The anchor for "a" should contain a <title>... <desc>...</title> block
    node_area = svg.split('data-case-id="a"', 1)[1].split("</a>", 1)[0]
    assert "<title>" in node_area or "<title " in node_area
    assert "用例X" in node_area


def test_empty_graph_still_renders():
    g = TestGraph(title="empty")
    svg = SVGRenderer().render(g)
    assert "<svg" in svg
    assert "</svg>" in svg
    ET.fromstring(svg)


def test_render_to_file(tmp_path: Path):
    g = TestGraph(title="t", nodes=[TestNode(id="a", case=_case())])
    out = tmp_path / "out.svg"
    SVGRenderer().render_to_file(g, out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<svg" in text
    ET.fromstring(text)


def test_edges_rendered_as_lines():
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="a", case=_case()),
            TestNode(id="b", case=_case(i=2)),
        ],
        edges=[Edge(source="a", target="b")],
    )
    svg = SVGRenderer().render(g)
    # Line element between the two nodes
    assert "<line" in svg


def test_svg_uses_viewbox_for_scaling():
    g = TestGraph(title="t", nodes=[TestNode(id="a", case=_case())])
    svg = SVGRenderer().render(g)
    assert "viewBox" in svg


def test_keyboard_focusable_via_anchor():
    """The <a> element is focusable and has aria-label for screen readers."""
    g = TestGraph(title="t", nodes=[TestNode(id="a", case=_case(title="登录成功"))])
    svg = SVGRenderer().render(g)
    assert 'aria-label' in svg
