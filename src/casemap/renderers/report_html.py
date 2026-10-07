"""Read-only test report HTML renderer (for export to PM/dev)."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from jinja2 import Template

from casemap._internal.exceptions import RenderError
from casemap.models.graph import TestGraph
from casemap.models.testcase import CaseType, TestStatus

_TYPE_LABEL = {
    CaseType.POSITIVE: "正向",
    CaseType.NEGATIVE: "逆向",
    CaseType.EDGE: "边界",
    CaseType.SECURITY: "安全",
}
_STATUS_LABEL = {
    TestStatus.PASSED: "通过",
    TestStatus.FAILED: "失败",
    TestStatus.BLOCKED: "阻塞",
    TestStatus.SKIPPED: "跳过",
    TestStatus.IN_PROGRESS: "进行中",
    TestStatus.PENDING: "待测",
}

REPORT_CSS = """\
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
       margin: 0; padding: 2rem; background: #f8fafc; color: #0f172a; }
.container { max-width: 960px; margin: 0 auto; background: white;
             padding: 2rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
h1 { margin: 0 0 1rem; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 1rem; margin: 1.5rem 0; }
.stat { padding: 1rem; border-radius: 6px; text-align: center; }
.stat .num { font-size: 1.75rem; font-weight: 600; }
.stat .label { font-size: 0.875rem; color: #64748b; }
.stat.passed { background: #d1fae5; }
.stat.failed { background: #fee2e2; }
.stat.pending { background: #f3f4f6; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { background: #f8fafc; font-weight: 600; }
.failed-section { margin-top: 2rem; padding: 1rem; background: #fef2f2;
                  border-left: 4px solid #ef4444; border-radius: 4px; }
.failed-item { padding: 0.5rem 0; border-bottom: 1px solid #fecaca; }
.failed-item:last-child { border-bottom: none; }
"""

TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} - 测试报告</title>
<style>{{ css|safe }}</style>
</head>
<body>
<div class="container">
<h1>{{ title }} - 测试报告</h1>
<p>生成时间：{{ generated_at }} · 共 {{ total }} 个用例</p>
<div class="summary">
  <div class="stat passed"><div class="num">{{ passed }}</div><div class="label">通过</div></div>
  <div class="stat failed"><div class="num">{{ failed }}</div><div class="label">失败</div></div>
  <div class="stat pending"><div class="num">{{ pending }}</div><div class="label">待测</div></div>
  <div class="stat pending"><div class="num">{{ in_progress }}</div><div class="label">进行中</div></div>
  <div class="stat pending"><div class="num">{{ blocked }}</div><div class="label">阻塞</div></div>
  <div class="stat pending"><div class="num">{{ skipped }}</div><div class="label">跳过</div></div>
</div>

{% if failures %}
<div class="failed-section">
  <h2>失败用例</h2>
  {% for f in failures %}
  <div class="failed-item">
    <strong>{{ f.title }}</strong> ({{ type_label[f.type] }})<br>
    <em>{{ f.note or '（无备注）' }}</em>
  </div>
  {% endfor %}
</div>
{% endif %}

<h2>全部用例</h2>
<table>
  <thead>
    <tr><th>用例</th><th>类型</th><th>状态</th><th>备注</th></tr>
  </thead>
  <tbody>
    {% for r in rows %}
    <tr>
      <td>{{ r.title }}</td>
      <td>{{ type_label[r.type] }}</td>
      <td>{{ status_label[r.status] }}</td>
      <td>{{ r.note or '' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>
</body>
</html>
""")


class ReportHTMLRenderer:
    """Read-only test report (email/IM friendly)."""

    def render(
        self,
        graph: TestGraph,
        statuses: dict[str, dict[str, str]],
    ) -> str:
        from datetime import datetime

        rows: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        counts = dict.fromkeys(TestStatus, 0)
        for n in graph.nodes:
            s = statuses.get(n.id, {}) or {}
            status = s.get("status", "pending")
            if status not in TestStatus._value2member_map_:
                status = "pending"
            counts[TestStatus(status)] += 1
            row = {
                "title": n.case.title,
                "type": n.case.type.value,
                "status": status,
                "note": s.get("note", ""),
            }
            rows.append(row)
            if status == "failed":
                failures.append(
                    {"title": n.case.title, "type": n.case.type.value, "note": row["note"]}
                )
        try:
            rendered: Any = TEMPLATE.render(
                title=graph.title,
                css=REPORT_CSS,
                generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                total=len(graph.nodes),
                passed=counts[TestStatus.PASSED],
                failed=counts[TestStatus.FAILED],
                pending=counts[TestStatus.PENDING],
                in_progress=counts[TestStatus.IN_PROGRESS],
                blocked=counts[TestStatus.BLOCKED],
                skipped=counts[TestStatus.SKIPPED],
                failures=failures,
                rows=rows,
                type_label=_TYPE_LABEL,
                status_label=_STATUS_LABEL,
            )
        except Exception as e:
            raise RenderError(f"Report render failed: {e}") from e
        return str(rendered)
