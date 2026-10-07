"""JSON export/import for status persistence."""

from __future__ import annotations

from typing import Any

import orjson

from casemap._internal.exceptions import RenderError
from casemap.models.graph import Edge, TestGraph, TestNode
from casemap.models.testcase import TestCase

_VERSION = 1


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


class JSONRenderer:
    """Render/parse TestGraph as JSON (round-trippable)."""

    def render(self, graph: TestGraph) -> str:
        payload = {
            "version": _VERSION,
            "graph": {
                "title": graph.title,
                "nodes": [{"id": n.id, "case": _to_dict(n.case)} for n in graph.nodes],
                "edges": [_to_dict(e) for e in graph.edges],
                "metadata": graph.metadata,
            },
        }
        return orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8")

    def parse(self, raw: str) -> TestGraph:
        try:
            data = orjson.loads(raw)
        except orjson.JSONDecodeError as e:
            raise RenderError(f"Invalid JSON: {e}") from e
        g = data.get("graph") or {}
        nodes = [
            TestNode(id=n["id"], case=TestCase.model_validate(n["case"]))
            for n in g.get("nodes", [])
        ]
        edges = [Edge.model_validate(e) for e in g.get("edges", [])]
        return TestGraph(
            title=g.get("title", ""),
            nodes=nodes,
            edges=edges,
            metadata=g.get("metadata", {}),
        )
