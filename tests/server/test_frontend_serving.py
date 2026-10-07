"""Frontend SPA serving — integration gap fix (SP-1/SP-3 wiring)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import casemap.server.models as models_module
from casemap.server.app import create_app
from casemap.server.db import get_db

INDEX_HTML = (
    '<!doctype html><html><head>'
    '<title>casemap SPA</title>'
    '<script type="module" src="/assets/main.js"></script>'
    '</head><body><div id="root"></div></body></html>'
)
ASSET_JS = 'console.log("casemap frontend bundle");\n'


@pytest.fixture
def fake_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Build a fake `frontend/dist/` and point CASEMAP_FRONTEND_DIST at it.

    After the test, the env var is restored (monkeypatch handles that).
    """
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "main.js").write_text(ASSET_JS)
    (tmp_path / "index.html").write_text(INDEX_HTML)
    monkeypatch.setenv("CASEMAP_FRONTEND_DIST", str(tmp_path))
    yield tmp_path


@pytest.fixture
def client(fake_dist: Path) -> Iterator[TestClient]:
    """TestClient wired to a fresh app + in-memory DB, with frontend enabled."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models_module.Base.metadata.create_all(engine)
    SessionT = sessionmaker(bind=engine, autoflush=False)
    app = create_app()

    def _override_db():
        sess = SessionT()
        try:
            yield sess
        finally:
            sess.close()

    app.dependency_overrides[get_db] = _override_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_root_serves_spa_index(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>casemap SPA</title>" in r.text
    assert "/assets/main.js" in r.text


def test_web_prefix_serves_spa(client: TestClient) -> None:
    """SPA routing — /web/* must return the same index.html (client-side route)."""
    r = client.get("/web/")
    assert r.status_code == 200
    assert "<title>casemap SPA</title>" in r.text


def test_deep_link_serves_spa(client: TestClient) -> None:
    """React Router paths like /projects/123 must resolve to the SPA shell."""
    r = client.get("/projects/123")
    assert r.status_code == 200
    assert "<title>casemap SPA</title>" in r.text


def test_unknown_spa_path_serves_index(client: TestClient) -> None:
    """Any non-API, non-docs path is a SPA route → index.html."""
    r = client.get("/some/totally/unknown/deep/link")
    assert r.status_code == 200
    assert "<title>casemap SPA</title>" in r.text


def test_assets_served(client: TestClient) -> None:
    r = client.get("/assets/main.js")
    assert r.status_code == 200
    assert "console.log" in r.text
    assert "casemap frontend bundle" in r.text


def test_api_routes_not_shadowed(client: TestClient) -> None:
    """Catch-all must NOT swallow /api/v1/* — those have real handlers.

    POST /api/v1/projects is unauthenticated (creates a project); using GET
    would 403 (admin-only) and prove nothing about route resolution.
    """
    r = client.post("/api/v1/projects", json={"name": "spa-test"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "spa-test"
    assert "project_api_key" in body


def test_api_unknown_path_returns_404(client: TestClient) -> None:
    """Unknown /api/v1/* path must 404 normally, not be served as SPA HTML."""
    r = client.get("/api/v1/no-such-resource")
    assert r.status_code == 404
    # Must NOT be the SPA shell.
    assert "casemap SPA" not in r.text


def test_docs_still_works(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower()


def test_openapi_json_still_works(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert body["info"]["title"] == "casemap server"


def test_assets_unknown_path_returns_404(client: TestClient) -> None:
    """Missing asset must 404, not fall through to the SPA shell."""
    r = client.get("/assets/does-not-exist.js")
    assert r.status_code == 404


def test_explicit_env_var_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If CASEMAP_FRONTEND_DIST points at a directory WITHOUT index.html,
    SPA serving is disabled and the placeholder / behavior takes over."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.setenv("CASEMAP_FRONTEND_DIST", str(empty_dir))
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models_module.Base.metadata.create_all(engine)
    SessionT = sessionmaker(bind=engine, autoflush=False)
    app = create_app()

    def _override_db():
        sess = SessionT()
        try:
            yield sess
        finally:
            sess.close()

    app.dependency_overrides[get_db] = _override_db
    try:
        with TestClient(app) as c:
            r = c.get("/")
            # No index.html in the fake dist → falls back to placeholder.
            assert r.status_code == 200
            assert "casemap server" in r.text
            # SPA catch-all was NOT registered, so unknown paths 404.
            assert c.get("/projects/123").status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
