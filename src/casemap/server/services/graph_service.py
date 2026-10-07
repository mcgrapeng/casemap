"""Graph service: parse spec → generate TestGraph → persist Graph + Cases."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from casemap.generators.pipeline import GenerationPipeline
from casemap.models.graph import TestGraph as CasemapTestGraph
from casemap.parsers.base import ParserRegistry
from casemap.renderers.html_self import HTMLSelfRenderer
from casemap.renderers.svg import SVGRenderer
from casemap.server.models import Case, Graph, Spec

_HTML = HTMLSelfRenderer()
_SVG = SVGRenderer()


def _detect_format(spec_format: str | None, raw_text: str) -> str:
    """Resolve "auto" → one of "openapi" | "postman" | "apifox"."""
    if spec_format and spec_format != "auto":
        return spec_format
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spec is not valid JSON: {e}",
        ) from e
    parser = ParserRegistry.auto_detect(data)
    if parser is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not auto-detect spec format. Pass ?format=openapi|postman|apifox",
        )
    return parser.name


def ingest_spec(
    db: Session,
    *,
    project_id: str,
    raw_text: str,
    spec_format: str | None,
    title: str | None = None,
) -> tuple[Spec, Graph]:
    """Parse spec → build TestGraph → persist Spec/Graph/Cases in one transaction.

    Returns the freshly-created (Spec, Graph) pair. Caller surfaces IDs.
    """
    fmt = _detect_format(spec_format, raw_text)
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spec is not valid JSON: {e}",
        ) from e

    parser = ParserRegistry.get(fmt)
    if parser is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown parser format: {fmt!r}",
        )
    endpoints = parser.parse(data)
    if not endpoints:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No endpoints parsed from spec",
        )

    pipeline = GenerationPipeline()
    graph: CasemapTestGraph = pipeline.run(
        endpoints, title=title or fmt
    )

    spec = Spec(
        id=str(uuid.uuid4()),
        project_id=project_id,
        raw_content=raw_text,
        format=fmt,
    )
    db.add(spec)
    db.flush()

    graph_row = Graph(
        id=str(uuid.uuid4()),
        spec_id=spec.id,
        project_id=project_id,
        title=graph.title,
        graph_data=graph.model_dump_json(),
        svg_content=_SVG.render(graph),
        html_content=_HTML.render(graph),
        case_count=len(graph.nodes),
    )
    db.add(graph_row)
    db.flush()

    for node in graph.nodes:
        case = Case(
            id=f"{project_id}:{node.id}",
            stable_id=node.id,
            graph_id=graph_row.id,
            project_id=project_id,
            type=node.case.type.value,
            title=node.case.title,
            description=node.case.description,
            steps=json.dumps([s.model_dump(mode="json") for s in node.case.steps]),
            endpoint_ref=node.case.endpoint_ref,
            tags=json.dumps(node.case.tags),
        )
        db.add(case)
    db.commit()
    db.refresh(spec)
    db.refresh(graph_row)
    return spec, graph_row


def get_graph(db: Session, project_id: str, graph_id: str) -> Graph:
    row = db.get(Graph, graph_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    return row


def render_graph_outputs(db: Session, project_id: str, graph_id: str) -> dict[str, Any]:
    """Return svg / html / report strings; raises 404 if missing."""
    row = get_graph(db, project_id, graph_id)
    statuses_map: dict[str, dict[str, Any]] = {}
    for case in row.cases:
        if case.status is not None:
            # Key by stable_id so the renderer (which knows node.id) matches;
            # fall back to case.id for legacy rows written before stable_id existed.
            key = case.stable_id or case.id
            statuses_map[key] = {
                "status": case.status.status,
                "note": case.status.note,
            }
    return {
        "svg": row.svg_content,
        "html": row.html_content,
        "graph_data": row.graph_data,
        "statuses": statuses_map,
    }


__all__ = ["ingest_spec", "get_graph", "render_graph_outputs"]
