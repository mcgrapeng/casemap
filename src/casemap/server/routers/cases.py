"""Cases router — list/get/update_status; progress."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.models import Case
from casemap.server.schemas import ProgressOut, StatusPatch
from casemap.server.services import ci_service

router = APIRouter(prefix="/projects/{project_id}", tags=["cases"])


def _case_to_dict(c: Case) -> dict[str, Any]:
    return {
        "id": c.id,
        "graph_id": c.graph_id,
        "project_id": c.project_id,
        "type": c.type,
        "title": c.title,
        "description": c.description,
        "steps": json.loads(c.steps),
        "endpoint_ref": c.endpoint_ref,
        "tags": json.loads(c.tags),
        "status": c.status.status if c.status is not None else "pending",
        "note": c.status.note if c.status is not None else "",
        "updated_at": c.status.updated_at if c.status is not None else None,
    }


@router.get("/cases")
def list_cases(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    rows = ci_service.list_cases_with_status(db, project_id, tag=tag)
    return [_case_to_dict(c) for c in rows]


@router.get("/cases/{case_id}")
def get_case(
    project_id: str,
    case_id: str,
    db: DbSession,
    _project: CurrentProject,
) -> dict[str, Any]:
    case = ci_service.get_case(db, project_id, case_id)
    return _case_to_dict(case)


@router.patch("/cases/{case_id}/status")
def patch_status(
    project_id: str,
    case_id: str,
    payload: StatusPatch,
    db: DbSession,
    _project: CurrentProject,
) -> dict[str, Any]:
    row = ci_service.update_case_status(
        db,
        project_id=project_id,
        case_id=case_id,
        status_value=payload.status,
        note=payload.note or "",
        source=payload.source,
    )
    return {
        "case_id": row.case_id,
        "status": row.status,
        "note": row.note,
        "source": row.source,
        "updated_at": row.updated_at,
    }


@router.get("/progress", response_model=ProgressOut)
def progress(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,
) -> ProgressOut:
    p = ci_service.progress(db, project_id)
    return ProgressOut(**p)  # type: ignore[arg-type]
