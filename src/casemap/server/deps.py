"""FastAPI dependencies (db session, current project, admin auth)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from casemap.server.auth import find_project_by_token
from casemap.server.config import get_settings
from casemap.server.db import get_db
from casemap.server.models import Project

DbSession = Annotated[Session, Depends(get_db)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (expected Bearer token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


def get_current_project(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Project:
    token = _bearer(authorization)
    project = find_project_by_token(db, token)
    if project is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return project


def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> bool:
    expected = get_settings().admin_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CASEMAP_SERVER_ADMIN_TOKEN is not configured on this server",
        )
    token = _bearer(authorization)
    if token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token mismatch")
    return True


CurrentProject = Annotated[Project, Depends(get_current_project)]
AdminOk = Annotated[bool, Depends(require_admin)]
