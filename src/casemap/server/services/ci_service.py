"""CI service: map CI test names → case IDs, persist statuses."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from casemap.server.models import Case, Status

_VALID_CI_STATUSES = {"passed", "failed"}


def apply_ci_report(
    db: Session,
    *,
    project_id: str,
    results: list[dict[str, str]],
) -> tuple[int, int]:
    """Apply CI results to existing cases; return (matched, unmatched).

    - Each result must carry `matched_case_id` (caller's responsibility; v1
      does no fuzzy matching).
    - Each update overwrites the existing Status row with source='ci'.
    - `unmatched` is the number of results whose ID did not resolve to a
      project-owned case; they are silently dropped (no partial write).
    """
    if not results:
        return 0, 0

    matched = 0
    unmatched = 0
    now = datetime.now(UTC)

    for r in results:
        case_id = r.get("matched_case_id")
        new_status = r.get("status")
        if case_id is None or new_status not in _VALID_CI_STATUSES:
            unmatched += 1
            continue
        case = db.get(Case, case_id)
        if case is None or case.project_id != project_id:
            unmatched += 1
            continue
        row = db.get(Status, case_id)
        if row is None:
            row = Status(
                case_id=case_id,
                project_id=project_id,
                status=new_status,
                note="",
                source="ci",
                updated_at=now,
            )
            db.add(row)
        else:
            row.status = new_status
            row.source = "ci"
            row.updated_at = now
        matched += 1
    db.commit()
    return matched, unmatched


def list_cases_with_status(
    db: Session,
    project_id: str,
    *,
    tag: str | None = None,
) -> list[Case]:
    """Return cases for a project (denormalized query), optionally filtered by tag."""
    q = db.query(Case).filter(Case.project_id == project_id)
    rows = q.all()
    if tag is not None:
        # ponytail: tags is JSON-as-text for v1; Python-side check is OK because
        # case_count per graph is bounded by endpoint_count. Add JSON1 index when
        # project grows past N candidates.
        out: list[Case] = []
        for c in rows:
            import json as _json

            tags = _json.loads(c.tags)
            if tag in tags:
                out.append(c)
        return out
    return rows


def get_case(db: Session, project_id: str, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if case is None or case.project_id != project_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    return case


def update_case_status(
    db: Session,
    *,
    project_id: str,
    case_id: str,
    status_value: str,
    note: str,
    source: str,
) -> Status:
    case = get_case(db, project_id, case_id)
    row = db.get(Status, case_id)
    if row is None:
        row = Status(
            case_id=case.id,
            project_id=project_id,
            status=status_value,
            note=note,
            source=source,
        )
        db.add(row)
    else:
        row.status = status_value
        row.note = note
        row.source = source
        row.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return row


def progress(db: Session, project_id: str) -> dict[str, float | int]:
    cases = list_cases_with_status(db, project_id)
    counts = {
        "pending": 0,
        "in_progress": 0,
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
    }
    for c in cases:
        s = c.status.status if c.status is not None else "pending"
        counts[s] = counts.get(s, 0) + 1
    total = len(cases)
    pct = round(counts["passed"] / total * 100, 2) if total else 0.0
    return {"total": total, **counts, "completion_pct": pct}


def bulk_import(
    db: Session,
    *,
    project_id: str,
    entries: list[dict[str, Any]],
) -> dict[str, int]:
    """Merge statuses from import payload.

    Spec rule: if entry's updated_at is newer than existing, take new;
    otherwise keep existing. Missing entries don't bump anything.
    """
    imported = 0
    skipped = 0
    now = datetime.now(UTC)
    for entry in entries:
        case_id = entry["case_id"]
        case = db.get(Case, case_id)
        if case is None or case.project_id != project_id:
            skipped += 1
            continue
        incoming_ts = entry.get("updated_at") or now
        existing = db.get(Status, case_id)
        # ponytail: SQLite default returns naive datetimes while we pass
        # tz-aware from the wire — normalize both sides to naive UTC for the
        # comparison. TZ-aware on Postgres.
        if existing is not None and existing.updated_at:
            existing_ts = existing.updated_at
            if existing_ts.tzinfo is None:
                existing_ts = existing_ts.replace(tzinfo=UTC)
            if incoming_ts.tzinfo is None:
                incoming_ts = incoming_ts.replace(tzinfo=UTC)
            if existing_ts > incoming_ts:
                skipped += 1
                continue
        if existing is None:
            row = Status(
                case_id=case_id,
                project_id=project_id,
                status=entry["status"],
                note=entry.get("note", ""),
                source=entry.get("source", "import"),
                updated_at=incoming_ts,
            )
            db.add(row)
        else:
            existing.status = entry["status"]
            existing.note = entry.get("note", "")
            existing.source = entry.get("source", "import")
            existing.updated_at = incoming_ts
        imported += 1
    db.commit()
    return {"imported": imported, "skipped": skipped}


def bulk_export(db: Session, project_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(Status)
        .filter(Status.project_id == project_id)
        .order_by(Status.case_id)
        .all()
    )
    return [
        {
            "case_id": r.case_id,
            "status": r.status,
            "note": r.note,
            "updated_at": r.updated_at,
            "source": r.source,
        }
        for r in rows
    ]


__all__ = [
    "apply_ci_report",
    "list_cases_with_status",
    "get_case",
    "update_case_status",
    "progress",
    "bulk_import",
    "bulk_export",
]
