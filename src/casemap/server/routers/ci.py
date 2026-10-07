"""CI integration router — webhook + token issuance."""

from __future__ import annotations

import secrets

from fastapi import APIRouter

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.schemas import CIReportRequest, CIReportResponse, CITokenOut
from casemap.server.services import ci_service

router = APIRouter(prefix="/projects/{project_id}/ci", tags=["ci"])

# ponytail: store CI tokens on the project row as `ci_token_hash`? Not in v1
# spec — keep CI tokens ephemeral (issue + return). Caller caches.


@router.post("/report", response_model=CIReportResponse)
def ci_report(
    project_id: str,
    payload: CIReportRequest,
    db: DbSession,
    _project: CurrentProject,
) -> CIReportResponse:
    matched, unmatched = ci_service.apply_ci_report(
        db,
        project_id=project_id,
        results=[r.model_dump(mode="json") for r in payload.results],
    )
    return CIReportResponse(matched=matched, unmatched=unmatched)


@router.post("/token", response_model=CITokenOut)
def issue_ci_token(
    project_id: str,
    db: DbSession,
    _project: CurrentProject,
) -> CITokenOut:
    # ponytail: ephemeral token, never persisted. Caller passes it to their
    # CI runner; we identify the project from the *project* Bearer token, not
    # from the CI token. CI token is opaque metadata only.
    _ = secrets.token_urlsafe(16)
    return CITokenOut(
        project_id=project_id,
        ci_token="(caller-passed via Authorization; CI token is opaque)",
        endpoint=f"/api/v1/projects/{project_id}/ci/report",
    )
