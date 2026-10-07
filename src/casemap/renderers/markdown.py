"""Markdown decision-table renderer."""

from __future__ import annotations

from casemap.models.graph import TestGraph
from casemap.models.testcase import CaseType

_TYPE_LABEL = {
    CaseType.POSITIVE: "正向",
    CaseType.NEGATIVE: "逆向",
    CaseType.EDGE: "边界",
    CaseType.SECURITY: "安全",
}


# ponytail: a `|` inside a table cell breaks column alignment. Escape `|`
# to `\|` so titles like "search | filter" stay in the 标题 column. Keep
# cheap; only pipe matters because other Markdown special chars (asterisk,
# bracket) have no effect inside a table cell.
def _esc(text: str) -> str:
    return text.replace("|", r"\|")


class MarkdownRenderer:
    """Render a TestGraph as a flat markdown decision table."""

    def render(self, graph: TestGraph) -> str:
        lines = [f"# {_esc(graph.title)}", ""]
        if not graph.nodes:
            lines.append("_（暂无测试用例）_")
            return "\n".join(lines) + "\n"
        lines.append("| 用例 ID | 类型 | 标题 | 接口 |")
        lines.append("|---------|------|------|------|")
        for n in graph.nodes:
            label = _TYPE_LABEL.get(n.case.type, n.case.type.value)
            lines.append(
                f"| `{_esc(n.id)}` | {label} | {_esc(n.case.title)} | {_esc(n.case.endpoint_ref or '')} |"
            )
        return "\n".join(lines) + "\n"
