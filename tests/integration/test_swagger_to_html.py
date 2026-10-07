"""End-to-end integration: Swagger spec → TestGraph → self-contained HTML."""

from __future__ import annotations

import json
from pathlib import Path

from casemap.generators.pipeline import GenerationPipeline
from casemap.parsers.openapi import OpenAPIParser
from casemap.renderers.html_self import HTMLSelfRenderer

SPEC = Path(__file__).parent.parent / "fixtures" / "petstore_swagger.json"


def test_swagger_spec_to_interactive_html():
    spec = json.loads(SPEC.read_text())
    endpoints = OpenAPIParser().parse(spec)
    assert len(endpoints) >= 4

    graph = GenerationPipeline().run(endpoints, title="Petstore")
    assert graph.title == "Petstore"
    assert len(graph.nodes) > 0

    html = HTMLSelfRenderer().render(graph)
    assert html.startswith("<!DOCTYPE html>")
    assert "Petstore" in html
    assert "<style>" in html
    # P0 #2 — we render inline SVG instead of Mermaid (zero CDN / zero external script).
    assert "<svg" in html.lower()
    assert "localStorage" in html


def test_html_can_be_loaded_by_browser():
    """Sanity check: produce a minimal HTML, ensure no syntax errors."""
    from casemap.models.graph import TestGraph, TestNode
    from casemap.models.testcase import CaseType, TestCase

    g = TestGraph(
        title="x",
        nodes=[TestNode(id="a", case=TestCase(id="a", type=CaseType.POSITIVE, title="t"))],
    )
    html = HTMLSelfRenderer().render(g)
    # Basic sanity: matched tags
    assert html.count("<html") == 1
    assert html.count("</html>") == 1
    assert html.count("<body") == 1
    assert html.count("</body>") == 1
