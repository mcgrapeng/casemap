"""Specs router — upload spec → trigger graph generation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile, status

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.schemas import SpecCreated, SpecOut
from casemap.server.services import graph_service

router = APIRouter(prefix="/projects/{project_id}/specs", tags=["specs"])


@router.post(
    "",
    response_model=SpecCreated,
    status_code=status.HTTP_201_CREATED,
)
async def upload_spec(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,  # bearer guard
    file: UploadFile = File(...),
    format: str | None = Form(default=None),
    title: str | None = Form(default=None),
) -> SpecCreated:
    raw = (await file.read()).decode("utf-8", errors="replace")
    spec, graph = graph_service.ingest_spec(
        db,
        project_id=project_id,
        raw_text=raw,
        spec_format=format,
        title=title,
    )
    return SpecCreated(
        spec_id=spec.id,
        graph_id=graph.id,
        case_count=graph.case_count,
    )


@router.get("", response_model=list[SpecOut])
def list_specs(project_id: str, db: DbSession, _project: CurrentProject) -> list[SpecOut]:
    from casemap.server.models import Spec  # noqa: PLC0415

    rows = (
        db.query(Spec)
        .filter(Spec.project_id == project_id)
        .order_by(Spec.created_at.desc())
        .all()
    )
    return [
        SpecOut(
            id=r.id,
            project_id=r.project_id,
            format=r.format,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{spec_id}")
def get_spec(
    project_id: str, spec_id: str, db: DbSession, _project: CurrentProject
) -> dict[str, Any]:
    from fastapi import HTTPException  # noqa: PLC0415

    from casemap.server.models import Graph, Spec  # noqa: PLC0415

    spec = db.get(Spec, spec_id)
    if spec is None or spec.project_id != project_id:
        raise HTTPException(status_code=404, detail="Spec not found")
    graph = (
        db.query(Graph).filter(Graph.spec_id == spec_id).order_by(Graph.created_at.desc()).first()
    )
    return {
        "id": spec.id,
        "project_id": spec.project_id,
        "format": spec.format,
        "created_at": spec.created_at,
        "graph_id": graph.id if graph else None,
        "case_count": graph.case_count if graph else 0,
    }
