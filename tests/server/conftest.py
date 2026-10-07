"""Shared fixtures for casemap.server tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import casemap.server.models as models_module
from casemap.server.app import create_app


@pytest.fixture
def app_with_db() -> Iterator[tuple]:
    """Fresh in-memory SQLite engine + FastAPI app with dependency override.
    StaticPool ensures all sessions share the same in-memory connection
    (otherwise each connection gets its own DB)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models_module.Base.metadata.create_all(engine)
    SessionT = sessionmaker(bind=engine, autoflush=False)
    app = create_app()

    from casemap.server.db import get_db  # noqa: PLC0415

    def _override_db():
        sess = SessionT()
        try:
            yield sess
        finally:
            sess.close()

    app.dependency_overrides[get_db] = _override_db
    try:
        yield app, engine, SessionT
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def client(app_with_db) -> Iterator[TestClient]:
    app, _, _ = app_with_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(app_with_db) -> Iterator[Session]:
    _, engine, SessionT = app_with_db
    sess = SessionT()
    try:
        yield sess
    finally:
        sess.close()
