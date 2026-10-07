"""Project service: create / fetch / delete / generate API key."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from casemap.server.auth import generate_project_api_key
from casemap.server.models import Project


def create_project(
    db: Session,
    *,
    name: str,
    llm_provider: str | None,
    llm_model: str | None,
) -> tuple[Project, str]:
    """Insert a new project; return (Project, raw_api_key).

    Raw key is shown ONCE — caller is responsible for surfacing it in the
    create response.
    """
    raw_key, hashed = generate_project_api_key()
    project = Project(
        id=str(uuid.uuid4()),
        name=name,
        api_key_hash=hashed,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    db.add(project)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # ponytail: IntegrityError is the only way the unique-name constraint
        # surfaces; raising it raw leaks SQLAlchemy details. Translate.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project name already exists: {name!r}",
        ) from e
    db.refresh(project)
    return project, raw_key


def delete_project(db: Session, project_id: str) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.delete(project)
    db.commit()


def list_projects(db: Session) -> list[Project]:
    return list(db.query(Project).order_by(Project.created_at.desc()).all())


def get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


__all__ = [
    "create_project",
    "delete_project",
    "list_projects",
    "get_project",
]
