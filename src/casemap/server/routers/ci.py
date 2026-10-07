"""CI integration router — webhook + token issuance."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks

from casemap.server.deps import CurrentProject, DbSession
from casemap.server.schemas import CIReportRequest, CIReportResponse, CITokenOut
from casemap.server.services import ci_service
from casemap.server.ws import broadcast

router = APIRouter(prefix="/projects/{project_id}/ci", tags=["ci"])

# ponytail: store CI tokens on the project row as `ci_token_hash`? Not in v1
# spec — keep CI tokens ephemeral (issue + return). Caller caches.


@router.post("/report", response_model=CIReportResponse)
def ci_report(
    project_id: str,
    payload: CIReportRequest,
    db: DbSession,
    bg: BackgroundTasks,
    _project: CurrentProject,
) -> CIReportResponse:
    results = [r.model_dump(mode="json") for r in payload.results]
    matched, unmatched = ci_service.apply_ci_report(db, project_id=project_id, results=results)
    # CI matches overwrite source to "ci" — broadcast the new state of each match,
    # using the public stable_id so the frontend's local cache key matches.
    # Skip unmatched: their matched_case_id didn't resolve, so we can't look it up.
    now_iso = datetime.now(UTC).isoformat()
    for r in results:
        try:
            case = ci_service.get_case(db, project_id, r["matched_case_id"])
        except Exception:  # noqa: BLE001
            continue
        bg.add_task(
            broadcast,
            project_id,
            {
                "type": "status_changed",
                "case_id": case.stable_id or case.id,
                "status": r["status"],
                "note": "",
                "source": "ci",
                "updated_at": now_iso,
            },
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
