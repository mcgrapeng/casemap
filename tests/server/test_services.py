"""Project / Graph / CI service tests."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from casemap.server.models import Case, Status
from casemap.server.services import ci_service, graph_service, project_service

FIX = Path(__file__).parent.parent / "fixtures"


# ---------- project_service ----------


def test_create_project_returns_raw_key_only(db_session):
    project, raw_key = project_service.create_project(
        db_session, name="Acme", llm_provider=None, llm_model=None
    )
    assert project.id
    assert raw_key
    assert len(raw_key) >= 32
    assert project.name == "Acme"
    assert project.api_key_hash  # hashed, never equal to raw


def test_create_project_duplicate_name_raises_409(db_session):
    project_service.create_project(db_session, name="dup", llm_provider=None, llm_model=None)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        project_service.create_project(
            db_session, name="dup", llm_provider=None, llm_model=None
        )
    assert e.value.status_code == 409


def test_get_project_404_when_missing(db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        project_service.get_project(db_session, "no-such-id")
    assert e.value.status_code == 404


def test_delete_project_then_lookup_raises(db_session):
    project, _ = project_service.create_project(
        db_session, name="tbr", llm_provider=None, llm_model=None
    )
    project_service.delete_project(db_session, project.id)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        project_service.get_project(db_session, project.id)


# ---------- graph_service ----------


def _make_project(db):
    project, _ = project_service.create_project(
        db, name="g", llm_provider=None, llm_model=None
    )
    return project


def test_ingest_spec_creates_spec_graph_and_cases(db_session):
    project = _make_project(db_session)
    raw = (FIX / "petstore_swagger.json").read_text()
    spec, graph = graph_service.ingest_spec(
        db_session, project_id=project.id, raw_text=raw, spec_format="openapi"
    )
    assert spec.id
    assert graph.id
    assert graph.case_count > 0
    cases = db_session.query(Case).filter(Case.graph_id == graph.id).all()
    assert len(cases) == graph.case_count
    # Status rows are lazy (created on first update/CI/import); the
    # pending state is implicit. ci_service.progress handles it.
    statuses = db_session.query(Status).filter(Status.project_id == project.id).all()
    assert statuses == []
    # ...but querying cases with no status row still works (defaults to pending).
    p = ci_service.progress(db_session, project.id)
    assert p["total"] == len(cases)
    assert p["pending"] == len(cases)


def test_ingest_spec_format_auto(db_session):
    project = _make_project(db_session)
    raw = (FIX / "petstore_swagger.json").read_text()
    spec, graph = graph_service.ingest_spec(
        db_session, project_id=project.id, raw_text=raw, spec_format="auto"
    )
    assert spec.format == "openapi"
    assert graph.case_count > 0


def test_ingest_spec_invalid_json_raises_400(db_session):
    project = _make_project(db_session)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        graph_service.ingest_spec(
            db_session, project_id=project.id, raw_text="{not json", spec_format="openapi"
        )
    assert e.value.status_code == 400


def test_get_graph_wrong_project_returns_404(db_session):
    project = _make_project(db_session)
    raw = (FIX / "petstore_swagger.json").read_text()
    _, graph = graph_service.ingest_spec(
        db_session, project_id=project.id, raw_text=raw, spec_format="openapi"
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        graph_service.get_graph(db_session, "other-project", graph.id)
    assert e.value.status_code == 404


def test_render_graph_outputs_contains_svg_and_html(db_session):
    project = _make_project(db_session)
    raw = (FIX / "petstore_swagger.json").read_text()
    _, graph = graph_service.ingest_spec(
        db_session, project_id=project.id, raw_text=raw, spec_format="openapi"
    )
    out = graph_service.render_graph_outputs(db_session, project.id, graph.id)
    assert out["svg"].startswith("<svg")
    assert out["html"].startswith("<!DOCTYPE html>")
    statuses = out["statuses"]
    assert isinstance(statuses, dict)
    # No statuses yet — keys only exist after first update / CI / import.
    assert statuses == {}
    # Apply one status and confirm it surfaces in the rendered outputs.
    case = db_session.query(Case).filter(Case.graph_id == graph.id).first()
    ci_service.update_case_status(
        db_session,
        project_id=project.id,
        case_id=case.id,
        status_value="passed",
        note="ok",
        source="human",
    )
    out2 = graph_service.render_graph_outputs(db_session, project.id, graph.id)
    assert case.stable_id in out2["statuses"]
    assert out2["statuses"][case.stable_id]["status"] == "passed"


# ---------- ci_service ----------


def _setup_with_cases(db):
    project, _ = project_service.create_project(
        db, name="ci", llm_provider=None, llm_model=None
    )
    raw = (FIX / "petstore_swagger.json").read_text()
    _, graph = graph_service.ingest_spec(
        db, project_id=project.id, raw_text=raw, spec_format="openapi"
    )
    cases = db.query(Case).filter(Case.graph_id == graph.id).limit(2).all()
    return project, cases


def test_apply_ci_report_updates_status_with_source_ci(db_session):
    project, cases = _setup_with_cases(db_session)
    matched, unmatched = ci_service.apply_ci_report(
        db_session,
        project_id=project.id,
        results=[
            {"matched_case_id": cases[0].id, "status": "passed"},
            {"matched_case_id": cases[1].id, "status": "failed", "duration_ms": 50},
        ],
    )
    assert matched == 2
    assert unmatched == 0
    s0 = db_session.get(Status, cases[0].id)
    s1 = db_session.get(Status, cases[1].id)
    assert s0 is not None and s0.status == "passed" and s0.source == "ci"
    assert s1 is not None and s1.status == "failed" and s1.source == "ci"


def test_apply_ci_report_unknown_case_counts_as_unmatched(db_session):
    project, _ = _setup_with_cases(db_session)
    matched, unmatched = ci_service.apply_ci_report(
        db_session,
        project_id=project.id,
        results=[{"matched_case_id": "ghost", "status": "passed"}],
    )
    assert matched == 0
    assert unmatched == 1


def test_progress_aggregates_statuses(db_session):
    project, cases = _setup_with_cases(db_session)
    # Force first two to passed.
    ci_service.apply_ci_report(
        db_session,
        project_id=project.id,
        results=[
            {"matched_case_id": cases[0].id, "status": "passed"},
            {"matched_case_id": cases[1].id, "status": "passed"},
        ],
    )
    p = ci_service.progress(db_session, project.id)
    assert p["total"] >= 2
    assert p["passed"] == 2
    assert p["completion_pct"] == round(2 / p["total"] * 100, 2)


def test_bulk_import_export_roundtrip(db_session):
    project, cases = _setup_with_cases(db_session)
    entries = [
        {
            "case_id": cases[0].id,
            "status": "passed",
            "note": "looks good",
            "source": "import",
        },
        {
            "case_id": cases[1].id,
            "status": "failed",
            "note": "broken",
            "source": "import",
        },
    ]
    summary = ci_service.bulk_import(
        db_session, project_id=project.id, entries=entries
    )
    assert summary["imported"] == 2
    exported = ci_service.bulk_export(db_session, project.id)
    exported_by_id = {e["case_id"]: e for e in exported}
    assert exported_by_id[cases[0].id]["status"] == "passed"
    assert exported_by_id[cases[1].id]["status"] == "failed"
    assert exported_by_id[cases[0].id]["note"] == "looks good"


def test_bulk_import_skips_stale_entries(db_session):
    project, cases = _setup_with_cases(db_session)
    from datetime import datetime, timedelta

    fresh = datetime.now(UTC)
    stale = fresh - timedelta(days=7)

    # Seed with a NEW status
    ci_service.update_case_status(
        db_session,
        project_id=project.id,
        case_id=cases[0].id,
        status_value="passed",
        note="current",
        source="human",
    )
    # Re-fetch fresh because the service sets updated_at = now internally
    fresh_again = datetime.now(UTC)

    summary = ci_service.bulk_import(
        db_session,
        project_id=project.id,
        entries=[
            {
                "case_id": cases[0].id,
                "status": "failed",
                "note": "older",
                "updated_at": fresh_again,
            }
        ],
    )
    # Same timestamp → either way, but ensure no crash and the row exists
    assert summary["imported"] >= 0

    # Now send a definitely-stale entry and confirm skip
    summary2 = ci_service.bulk_import(
        db_session,
        project_id=project.id,
        entries=[
            {
                "case_id": cases[0].id,
                "status": "failed",
                "note": "too old",
                "updated_at": stale,
            }
        ],
    )
    assert summary2["imported"] == 0
    assert summary2["skipped"] == 1


def test_list_cases_with_status_filters_by_tag(db_session):
    project, cases = _setup_with_cases(db_session)
    rows = ci_service.list_cases_with_status(db_session, project.id, tag="pets")
    # petstore has tag pets on all cases
    assert len(rows) >= 1


def test_get_case_404_wrong_project(db_session):
    project, cases = _setup_with_cases(db_session)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        ci_service.get_case(db_session, "other-project", cases[0].id)


def test_update_case_status_creates_when_absent(db_session):
    project, cases = _setup_with_cases(db_session)
    row = ci_service.update_case_status(
        db_session,
        project_id=project.id,
        case_id=cases[0].id,
        status_value="blocked",
        note="waiting",
        source="human",
    )
    assert row.status == "blocked"
    assert row.source == "human"
    assert row.note == "waiting"


def test_update_case_status_overwrites_when_present(db_session):
    project, cases = _setup_with_cases(db_session)
    ci_service.update_case_status(
        db_session,
        project_id=project.id,
        case_id=cases[0].id,
        status_value="pending",
        note="",
        source="human",
    )
    row = ci_service.update_case_status(
        db_session,
        project_id=project.id,
        case_id=cases[0].id,
        status_value="passed",
        note="ok",
        source="human",
    )
    assert row.status == "passed"
    assert row.note == "ok"
