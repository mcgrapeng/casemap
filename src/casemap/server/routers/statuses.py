"""Statuses router — bulk import/export (cross-device sync)."""

from __future__ import annotations

from fastapi import APIRouter

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.schemas import (
    BulkExportEntry,
    BulkExportResponse,
    BulkImportRequest,
)
from casemap.server.services import ci_service

router = APIRouter(prefix="/projects/{project_id}/statuses", tags=["statuses"])


@router.post("/import")
def bulk_import(
    project_id: str,
    payload: BulkImportRequest,
    db: DbSession,
    _project: CurrentProject,
) -> dict[str, int]:
    return ci_service.bulk_import(
        db,
        project_id=project_id,
        entries=[e.model_dump(mode="json") for e in payload.entries],
    )


@router.get("/export", response_model=BulkExportResponse)
def bulk_export(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,
) -> BulkExportResponse:
    rows = ci_service.bulk_export(db, project_id)
    entries = [BulkExportEntry(**r) for r in rows]
    return BulkExportResponse(entries=entries)
