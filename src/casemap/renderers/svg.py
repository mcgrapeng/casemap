"""Inline SVG renderer for TestGraph (Task 11, post P0 fix).

Replaces the planned Mermaid renderer: zero external deps, layered-by-tag
layout, every node is a keyboard-clickable SVG <a> for click handling.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from casemap.models.graph import TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus

COLUMN_WIDTH = 280
ROW_HEIGHT = 90
PADDING = 40
NODE_WIDTH = 240
NODE_HEIGHT = 64

_CASE_TYPE_EMOJI: dict[CaseType, str] = {
    CaseType.POSITIVE: "\u2705",
    CaseType.NEGATIVE: "\u274c",
    CaseType.EDGE: "\U0001f536",  # 🔶 large orange diamond
    CaseType.SECURITY: "\U0001f6e1",  # 🛡 shield
}

_CASE_TYPE_ORDER: dict[CaseType, int] = {
    CaseType.POSITIVE: 0,
    CaseType.NEGATIVE: 1,
    CaseType.EDGE: 2,
    CaseType.SECURITY: 3,
}

_STATUS_FILLS: dict[TestStatus, str] = {
    TestStatus.PENDING: "#f3f4f6",
    TestStatus.IN_PROGRESS: "#fef3c7",
    TestStatus.PASSED: "#d1fae5",
    TestStatus.FAILED: "#fee2e2",
    TestStatus.BLOCKED: "#e5e7eb",
    TestStatus.SKIPPED: "#dbeafe",
}

_STATUS_STROKES: dict[TestStatus, str] = {
    TestStatus.PENDING: "#9ca3af",
    TestStatus.IN_PROGRESS: "#f59e0b",
    TestStatus.PASSED: "#10b981",
    TestStatus.FAILED: "#ef4444",
    TestStatus.BLOCKED: "#6b7280",
    TestStatus.SKIPPED: "#3b82f6",
}

UNTAGGED_KEY = "\uffff"  # sort untagged nodes last


class SVGRenderer:
    """Render a TestGraph as a self-contained SVG string."""

    def render(self, graph: TestGraph) -> str:
        positions = self._compute_positions(graph.nodes)
        width = PADDING * 2 + max(len(self._group_by_tag(graph.nodes)), 1) * COLUMN_WIDTH
        rows = max(
            (self._row_in_group(graph.nodes, node.id) + 1 for node in graph.nodes),
            default=1,
        )
        height = PADDING * 2 + max(rows, 1) * ROW_HEIGHT

        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'font-family="system-ui, -apple-system, sans-serif">',
            f"<title>{xml_escape(graph.title)}</title>",
        ]

        for edge in graph.edges:
            line = self._render_edge(edge.source, edge.target, positions)
            if line:
                parts.append(line)

        for node in graph.nodes:
            if node.id in positions:
                parts.append(self._render_node(node, *positions[node.id]))

        parts.append("</svg>")
        return "\n".join(parts)

    def render_to_file(self, graph: TestGraph, path: Path) -> None:
        path.write_text(self.render(graph), encoding="utf-8")

    def _compute_positions(self, nodes: list[TestNode]) -> dict[str, tuple[float, float]]:
        groups = self._group_by_tag(nodes)
        positions: dict[str, tuple[float, float]] = {}
        for col, (_tag, group_nodes) in enumerate(groups.items()):
            ordered = sorted(
                group_nodes,
                key=lambda n: (_CASE_TYPE_ORDER.get(n.case.type, 99), n.id),
            )
            for row, node in enumerate(ordered):
                x = PADDING + col * COLUMN_WIDTH
                y = PADDING + row * ROW_HEIGHT
                positions[node.id] = (x, y)
        return positions

    def _row_in_group(self, nodes: list[TestNode], node_id: str) -> int:
        groups = self._group_by_tag(nodes)
        for group_nodes in groups.values():
            ordered = sorted(
                group_nodes,
                key=lambda n: (_CASE_TYPE_ORDER.get(n.case.type, 99), n.id),
            )
            for row, n in enumerate(ordered):
                if n.id == node_id:
                    return row
        return 0

    @staticmethod
    def _group_by_tag(nodes: list[TestNode]) -> dict[str, list[TestNode]]:
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (n.case.tags[0] if n.case.tags else UNTAGGED_KEY, n.id),
        )
        groups: dict[str, list[TestNode]] = {}
        for n in sorted_nodes:
            tag = n.case.tags[0] if n.case.tags else "untagged"
            groups.setdefault(tag, []).append(n)
        return groups

    @staticmethod
    def _render_edge(
        source_id: str,
        target_id: str,
        positions: dict[str, tuple[float, float]],
    ) -> str | None:
        if source_id not in positions or target_id not in positions:
            return None
        sx, sy = positions[source_id]
        tx, ty = positions[target_id]
        x1 = sx + NODE_WIDTH / 2
        y1 = sy + NODE_HEIGHT
        x2 = tx + NODE_WIDTH / 2
        y2 = ty
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#cbd5e1" stroke-width="2"/>'
        )

    @staticmethod
    def _render_node(node: TestNode, x: float, y: float) -> str:
        case: TestCase = node.case
        fill = _STATUS_FILLS.get(case.status, "#f3f4f6")
        stroke = _STATUS_STROKES.get(case.status, "#9ca3af")
        emoji = _CASE_TYPE_EMOJI.get(case.type, "")
        label = xml_escape(case.title)
        cid = xml_escape(node.id)
        aria = xml_escape(f"{case.title} ({case.status.value})")
        title = xml_escape(f"{case.title}\nStatus: {case.status.value}")

        shape = _render_shape(case.type, x, y, fill, stroke)
        text_y = y + NODE_HEIGHT / 2 + 5
        text = (
            f'<text x="{x + NODE_WIDTH / 2}" y="{text_y}" text-anchor="middle" '
            f'font-size="14" fill="#1f2937">{xml_escape(emoji)} {label}</text>'
        )

        return (
            f'<a data-case-id="{cid}" href="#case-{cid}" '
            f'class="case-node" x="{x}" y="{y}" aria-label="{aria}">'
            f"<title>{title}</title>"
            f"{shape}"
            f"{text}"
            f"</a>"
        )


def _render_shape(case_type: CaseType, x: float, y: float, fill: str, stroke: str) -> str:
    if case_type in (CaseType.POSITIVE, CaseType.NEGATIVE):
        return (
            f'<rect x="{x}" y="{y}" width="{NODE_WIDTH}" height="{NODE_HEIGHT}" '
            f'rx="8" ry="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
    if case_type == CaseType.EDGE:
        cx = x + NODE_WIDTH / 2
        cy = y + NODE_HEIGHT / 2
        pts = (
            f"{cx},{y} "
            f"{x + NODE_WIDTH},{cy} "
            f"{cx},{y + NODE_HEIGHT} "
            f"{x},{cy}"
        )
        return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if case_type == CaseType.SECURITY:
        cx = x + NODE_WIDTH / 2
        top = y
        mid = y + NODE_HEIGHT / 2
        bot = y + NODE_HEIGHT
        d = (
            f"M {x},{top + 10} "
            f"Q {x},{top} {x + 20},{top} "
            f"L {x + NODE_WIDTH - 20},{top} "
            f"Q {x + NODE_WIDTH},{top} {x + NODE_WIDTH},{top + 10} "
            f"L {x + NODE_WIDTH},{mid + 6} "
            f"Q {x + NODE_WIDTH},{bot} {cx},{bot} "
            f"Q {x},{bot} {x},{mid + 6} Z"
        )
        return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    return (
        f'<rect x="{x}" y="{y}" width="{NODE_WIDTH}" height="{NODE_HEIGHT}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    )
