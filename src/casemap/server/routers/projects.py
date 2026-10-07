"""Projects router — CRUD on Project rows."""

from __future__ import annotations

from fastapi import APIRouter, status

from casemap.server.deps import AdminOk, CurrentProject, DbSession
from casemap.server.models import Project
from casemap.server.schemas import ProjectCreate, ProjectCreated, ProjectOut
from casemap.server.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at,
        updated_at=p.updated_at,
        llm_provider=p.llm_provider,
        llm_model=p.llm_model,
    )


@router.post("", response_model=ProjectCreated, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession) -> ProjectCreated:
    project, raw_key = project_service.create_project(
        db,
        name=payload.name,
        llm_provider=payload.llm_provider,
        llm_model=payload.llm_model,
    )
    out = _to_out(project).model_dump()
    out["project_api_key"] = raw_key
    return ProjectCreated(**out)


@router.get("", response_model=list[ProjectOut])
def list_projects(_admin: AdminOk, db: DbSession) -> list[ProjectOut]:
    return [_to_out(p) for p in project_service.list_projects(db)]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: DbSession, project: CurrentProject) -> ProjectOut:
    # ponytail: project lookup must use the caller's Bearer token, not just any
    # project_id. We require CurrentProject (which is the bearer-derived row)
    # and assert the path id matches it. Mismatch → 404.
    if project.id != project_id:
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(status_code=404, detail="Project not found")
    return _to_out(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str, db: DbSession, project: CurrentProject
) -> None:
    if project.id != project_id:
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(status_code=404, detail="Project not found")
    project_service.delete_project(db, project_id)
