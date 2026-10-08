"""Brain map output router — SVG, HTML, report for a Graph."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from casemap.renderers.report_html import ReportHTMLRenderer
from casemap.server.deps import CurrentProject, DbSession
from casemap.server.services.graph_service import render_graph_outputs

router = APIRouter(
    prefix="/projects/{project_id}/graphs/{graph_id}", tags=["brain-map"]
)


_REPORT = ReportHTMLRenderer()


def _payload(db: DbSession, project_id: str, graph_id: str) -> dict[str, Any]:
    return render_graph_outputs(db, project_id, graph_id)


@router.get("/svg", response_class=Response)
def graph_svg(
    project_id: str, graph_id: str, db: DbSession, _project: CurrentProject
) -> Response:
    p = _payload(db, project_id, graph_id)
    return Response(content=p["svg"], media_type="image/svg+xml")


@router.get("/html", response_class=Response)
def graph_html(
    project_id: str, graph_id: str, db: DbSession, _project: CurrentProject
) -> Response:
    p = _payload(db, project_id, graph_id)
    return Response(content=p["html"], media_type="text/html; charset=utf-8")


@router.get("/report", response_class=Response)
def graph_report(
    project_id: str, graph_id: str, db: DbSession, _project: CurrentProject
) -> Response:
    p = _payload(db, project_id, graph_id)
    graph_obj = json.loads(p["graph_data"])
    from casemap.models.graph import TestGraph as _TG  # noqa: PLC0415

    tg = _TG.model_validate(graph_obj)
    rendered = _REPORT.render(tg, statuses=p["statuses"])
    return Response(content=rendered, media_type="text/html; charset=utf-8")


@router.get("/graph.json")
def graph_data(
    project_id: str, graph_id: str, db: DbSession, _project: CurrentProject
) -> JSONResponse:
    p = _payload(db, project_id, graph_id)
    # ponytail: SPA-facing shape — flattened nodes with x/y/width/height + the
    # whole-graph width/height. Falls back to the raw model dump for clients
    # that don't speak the React brain-map vocabulary (CLI tooling, debugging).
    enriched = p.get("enriched_graph")
    if enriched is not None:
        return JSONResponse(content={"graph": enriched, "statuses": p["statuses"]})
    return JSONResponse(content={"graph": json.loads(p["graph_data"]), "statuses": p["statuses"]})
