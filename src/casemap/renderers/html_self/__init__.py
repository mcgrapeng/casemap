"""Self-contained HTML renderer (Task 13, post P0 fix).

Renders a single, offline HTML file with:
  - inline SVG (no Mermaid, no CDN — Task 11 SVGRenderer reused)
  - inline CSS + JS (zero external resources)
  - localStorage status persistence (per-browser)
  - status export / import mechanism (cross-browser / cross-device)
  - beforeunload guard when statuses are dirty
"""

from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

from jinja2 import Template as JinjaTemplate

from casemap._internal.exceptions import RenderError
from casemap.models.graph import TestGraph, TestNode
from casemap.models.testcase import TestStatus
from casemap.renderers.html_self.template import (
    CSS,
    HTML_TEMPLATE,
    INITIAL_STATUSES_JS,
    JS_INTERACTIVE,
)
from casemap.renderers.svg import SVGRenderer

__all__ = ["HTMLSelfRenderer"]


def _safe_json_for_script(payload: dict[str, Any] | list[Any] | str | int | float | bool | None) -> str:
    """JSON-encoded but HTML-safe for embedding inside a <script> block.

    Browsers terminate <script> at the first </script> they see, even inside
    a JS string literal. Escape </ -> <\\/ so the payload round-trips to
    identical JSON but cannot break out of the script element.
    """
    raw = json.dumps(payload, ensure_ascii=False)
    return raw.replace("</", "<\\/")


class HTMLSelfRenderer:
    """Render a TestGraph as a single self-contained HTML file."""

    def __init__(self) -> None:
        self._svg = SVGRenderer()
        self._template = JinjaTemplate(HTML_TEMPLATE)

    def render(
        self,
        graph: TestGraph,
        statuses: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        svg_graph = self._apply_statuses(graph, statuses) if statuses else graph
        svg = self._svg.render(svg_graph)

        cases_dict = {n.id: n.case.model_dump(mode="json") for n in graph.nodes}
        node_to_case = {n.id: n.id for n in graph.nodes}

        # ponytail: explicit placeholders, no $-pattern interpretation against
        # user-controlled JSON. Three known keys, three plain replace() calls.
        sentinels = {
            "$statuses_json": _safe_json_for_script(statuses or {}),
            "$cases_json": _safe_json_for_script(cases_dict),
            "$node_to_case_json": _safe_json_for_script(node_to_case),
        }
        init_js = INITIAL_STATUSES_JS
        for k, v in sentinels.items():
            init_js = init_js.replace(k, v)
        try:
            rendered: Any = self._template.render(
                title=graph.title,
                css=CSS,
                svg=svg,
                init_js=init_js,
                js=JS_INTERACTIVE,
            )
        except Exception as e:
            raise RenderError(f"HTML render failed: {e}") from e
        return str(rendered)

    @staticmethod
    def _apply_statuses(
        graph: TestGraph,
        statuses: dict[str, dict[str, Any]],
    ) -> TestGraph:
        """Return a copy of graph with statuses merged into each node's case.

        The SVG renderer colors nodes by `case.status`, so applying statuses
        before SVG render makes the initial view match the saved state.
        """
        updated: list[TestNode] = []
        for node in graph.nodes:
            s = statuses.get(node.id)
            if not s:
                updated.append(node)
                continue
            patch: dict[str, Any] = {}
            raw_status = s.get("status")
            if isinstance(raw_status, str):
                with suppress(ValueError):
                    patch["status"] = TestStatus(raw_status)
            if isinstance(s.get("note"), str):
                patch["failure_note"] = s["note"]
            updated.append(
                node.model_copy(update={"case": node.case.model_copy(update=patch)})
                if patch
                else node
            )
        return graph.model_copy(update={"nodes": updated})
