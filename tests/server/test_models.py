"""ORM schema tests (SP-2)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from casemap.server.models import Base, Case, Graph, Project, Spec, Status


def test_base_metadata_has_all_tables():
    """All five ORM models must be registered in Base.metadata."""
    names = set(Base.metadata.tables.keys())
    assert {"projects", "specs", "graphs", "cases", "statuses"} <= names


def test_create_project_minimal(db_session):
    p = Project(id=str(uuid.uuid4()), name="Acme", api_key_hash="x" * 64)
    db_session.add(p)
    db_session.commit()
    fetched = db_session.get(Project, p.id)
    assert fetched is not None
    assert fetched.name == "Acme"
    assert fetched.api_key_hash == "x" * 64
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
    assert fetched.llm_provider is None
    assert fetched.llm_model is None


def test_project_name_must_be_unique(db_session):
    a = Project(id=str(uuid.uuid4()), name="dup", api_key_hash="a" * 64)
    b = Project(id=str(uuid.uuid4()), name="dup", api_key_hash="b" * 64)
    db_session.add(a)
    db_session.commit()
    db_session.add(b)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_spec_cascade_deletes_from_project(db_session):
    project = Project(id=str(uuid.uuid4()), name="p", api_key_hash="h" * 64)
    spec = Spec(id=str(uuid.uuid4()), project=project, raw_content="{}", format="openapi")
    db_session.add_all([project, spec])
    db_session.commit()
    db_session.delete(project)
    db_session.commit()
    assert db_session.get(Spec, spec.id) is None


def test_graph_round_trip_serializes_testgraph(db_session):
    """graph_data column accepts any JSON-serializable payload."""
    project = Project(id=str(uuid.uuid4()), name="p", api_key_hash="h" * 64)
    spec = Spec(id=str(uuid.uuid4()), project=project, raw_content="{}", format="openapi")
    payload = '{"title": "x", "nodes": [], "edges": [], "metadata": {}}'
    graph = Graph(
        id=str(uuid.uuid4()),
        spec=spec,
        project=project,
        title="x",
        graph_data=payload,
        svg_content="<svg/>",
        html_content="<html/>",
        case_count=0,
    )
    db_session.add_all([project, spec, graph])
    db_session.commit()
    fetched = db_session.get(Graph, graph.id)
    assert fetched is not None
    assert fetched.title == "x"
    assert fetched.graph_data == payload
    assert fetched.case_count == 0


def test_case_status_round_trip(db_session):
    """Status row keyed by case_id (PK), not auto-increment id."""
    project = Project(id=str(uuid.uuid4()), name="p", api_key_hash="h" * 64)
    spec = Spec(id=str(uuid.uuid4()), project=project, raw_content="{}", format="openapi")
    graph = Graph(
        id=str(uuid.uuid4()),
        spec=spec,
        project=project,
        title="x",
        graph_data="{}",
        svg_content="",
        html_content="",
        case_count=1,
    )
    case = Case(
        id="case-abc",
        graph=graph,
        project=project,
        type="positive",
        title="Login works",
        description="",
        steps="[]",
        endpoint_ref="POST /login",
        tags='["auth"]',
    )
    status = Status(case_id=case.id, project=project, status="pending", note="", source="human")
    db_session.add_all([project, spec, graph, case, status])
    db_session.commit()
    fetched = db_session.get(Status, "case-abc")
    assert fetched is not None
    assert fetched.status == "pending"
    assert fetched.source == "human"
    assert fetched.updated_at is not None


def test_status_cascade_with_case(db_session):
    """Deleting the project cascades through case and status."""
    project = Project(id=str(uuid.uuid4()), name="p", api_key_hash="h" * 64)
    spec = Spec(id=str(uuid.uuid4()), project=project, raw_content="{}", format="openapi")
    graph = Graph(
        id=str(uuid.uuid4()),
        spec=spec,
        project=project,
        title="x",
        graph_data="{}",
        svg_content="",
        html_content="",
        case_count=1,
    )
    case = Case(
        id="case-x",
        graph=graph,
        project=project,
        type="positive",
        title="t",
        description="",
        steps="[]",
        endpoint_ref="",
        tags="[]",
    )
    status = Status(case_id=case.id, project=project, status="passed", note="ok", source="ci")
    db_session.add_all([project, spec, graph, case, status])
    db_session.commit()
    db_session.delete(project)
    db_session.commit()
    assert db_session.get(Case, "case-x") is None
    assert db_session.get(Status, "case-x") is None
