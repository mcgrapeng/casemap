"""Statuses router — bulk import/export (cross-device sync)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.schemas import (
    BulkExportEntry,
    BulkExportResponse,
    BulkImportRequest,
)
from casemap.server.services import ci_service
from casemap.server.ws import broadcast

router = APIRouter(prefix="/projects/{project_id}/statuses", tags=["statuses"])


@router.post("/import")
def bulk_import(
    project_id: str,
    payload: BulkImportRequest,
    db: DbSession,
    bg: BackgroundTasks,
    _project: CurrentProject,
) -> dict[str, int]:
    entries = [e.model_dump(mode="json") for e in payload.entries]
    result = ci_service.bulk_import(db, project_id=project_id, entries=entries)
    # Broadcast every imported entry (new + overwritten). source="import".
    for e in entries:
        bg.add_task(
            broadcast,
            project_id,
            {
                "type": "status_changed",
                "case_id": e["case_id"],
                "status": e["status"],
                "note": e.get("note", ""),
                "source": e.get("source", "import"),
                "updated_at": (
                    e["updated_at"].isoformat()
                    if hasattr(e.get("updated_at"), "isoformat")
                    else e.get("updated_at")
                ),
            },
        )
    return result


@router.get("/export", response_model=BulkExportResponse)
def bulk_export(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,
) -> BulkExportResponse:
    rows = ci_service.bulk_export(db, project_id)
    entries = [BulkExportEntry(**r) for r in rows]
    return BulkExportResponse(entries=entries)
