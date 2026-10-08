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

    # ponytail: enrich the SPA-facing graph payload with the layout fields the
    # React brain-map component expects (x/y/width/height + flattened
    # type/title/tags at the node level). Computed at request time so the
    # stored graph_data stays minimal and the layout algorithm stays in one
    # place (SVGRenderer). One extra import; cached on next request via
    # React Query in the SPA.
    from casemap.models.graph import TestGraph as _ModelGraph
    from casemap.renderers.svg import (
        COLUMN_WIDTH,
        NODE_HEIGHT,
        NODE_WIDTH,
        PADDING,
        ROW_HEIGHT,
        SVGRenderer,
    )

    raw = json.loads(row.graph_data)
    model_graph = _ModelGraph.model_validate(raw)
    positions = SVGRenderer()._compute_positions(model_graph.nodes)
    flat_nodes = []
    for n in raw["nodes"]:
        x, y = positions.get(n["id"], (PADDING, PADDING))
        flat_nodes.append(
            {
                "id": n["id"],
                "type": n["case"]["type"],
                "title": n["case"]["title"],
                "tags": n["case"].get("tags", []),
                "endpoint_ref": n["case"].get("endpoint_ref"),
                "x": x,
                "y": y,
                "width": NODE_WIDTH,
                "height": NODE_HEIGHT,
            }
        )
    flat_edges = [
        {"from": e.get("source") or e.get("from"), "to": e.get("target") or e.get("to")}
        for e in raw["edges"]
    ]
    groups: set[str] = {
        (n["case"].get("tags", [None]) or [None])[0] or "untagged" for n in raw["nodes"]
    }
    rows_per_group = max(
        (
            sum(
                1
                for n in raw["nodes"]
                if ((n["case"].get("tags", [None]) or [None])[0] or "untagged") == g
            )
            for g in groups
        ),
        default=1,
    )
    enriched_graph = {
        "nodes": flat_nodes,
        "edges": flat_edges,
        "width": PADDING * 2 + max(len(groups), 1) * COLUMN_WIDTH,
        "height": PADDING * 2 + rows_per_group * ROW_HEIGHT,
    }

    return {
        "svg": row.svg_content,
        "html": row.html_content,
        "graph_data": row.graph_data,
        "statuses": statuses_map,
        # ponytail: SPA-facing enriched payload lives alongside the raw model
        # dump so the legacy /graphs/{id}/svg + /html renderers keep working.
        "enriched_graph": enriched_graph,
    }


__all__ = ["ingest_spec", "get_graph", "render_graph_outputs"]
