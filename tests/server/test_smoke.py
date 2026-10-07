"""End-to-end smoke test (curl-equivalent) for casemap server.

Documents the manual smoke-test recipe in code form. Spawns uvicorn in
a background thread (no subprocess pipe deadlocks) and exercises the full
request/response cycle including multipart upload.

Marked with `pytest.mark.slow` so the default test run skips it. Run with:
    uv run pytest tests/server/test_smoke.py -m slow
or skip with:
    uv run pytest -m "not slow"
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import casemap.server.db as db_module
import casemap.server.models as models_module
from casemap.server.app import create_app

FIX = Path(__file__).parent.parent / "fixtures"
PETSTORE = FIX / "petstore_swagger.json"

pytestmark = pytest.mark.slow


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _client(timeout: float = 5.0) -> httpx.Client:
    """httpx client that ignores system proxies (some envs auto-route to 7890)."""
    return httpx.Client(timeout=timeout, trust_env=False)


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Run uvicorn in a background thread against a tmp SQLite DB.

    Swaps casemap.server.db.engine BEFORE create_app() so the test never
    touches the default sqlite:///./casemap.db left over from earlier runs.
    """
    port = _free_port()
    db_path = tmp_path_factory.mktemp("casemap") / "smoke.db"
    if db_path.exists():
        db_path.unlink()
    test_engine = create_engine(f"sqlite:///{db_path}")
    models_module.Base.metadata.create_all(test_engine)
    db_module.engine.dispose()
    db_module.engine = test_engine
    db_module.SessionLocal = sessionmaker(bind=test_engine, autoflush=False)
    print(f"\n[smoke] db_path={db_path}  port={port}")
    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        env_file=None,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        if server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"server never signaled started (port {port})")
    try:
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_create_then_spec_then_outputs(live_server: str):
    """Full curl-equivalent flow against a live uvicorn process."""
    with _client() as c:
        r = c.post(f"{live_server}/api/v1/projects", json={"name": "smoke"})
        assert r.status_code == 201, r.text
        body = r.json()
        project_id = body["id"]
        api_key = body["project_api_key"]
        assert project_id and api_key

        files = {"file": ("petstore.json", PETSTORE.read_text(), "application/json")}
        r = c.post(
            f"{live_server}/api/v1/projects/{project_id}/specs",
            files=files,
            data={"format": "openapi"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 201, r.text
        created = r.json()
        graph_id = created["graph_id"]
        case_count = created["case_count"]
        assert case_count > 0

        r = c.get(
            f"{live_server}/api/v1/projects/{project_id}/graphs/{graph_id}/html",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        html = r.text
        assert "<svg" in html.lower()
        assert "localStorage" in html

        r = c.get(
            f"{live_server}/api/v1/projects/{project_id}/cases",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        cases = r.json()
        assert len(cases) == case_count
        first = cases[0]

        r = c.patch(
            f"{live_server}/api/v1/projects/{project_id}/cases/{first['id']}/status",
            json={"status": "passed", "note": "ok"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "passed"

        r = c.get(
            f"{live_server}/api/v1/projects/{project_id}/progress",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        p = r.json()
        assert p["passed"] == 1
        assert p["total"] == case_count

        r = c.get(
            f"{live_server}/api/v1/projects/{project_id}/graphs/{graph_id}/svg",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        assert "svg" in r.headers["content-type"]
        assert r.text.startswith("<svg")

        r = c.get(
            f"{live_server}/api/v1/projects/{project_id}/graphs/{graph_id}/report",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


def test_live_server_rejects_bad_bearer(live_server: str):
    """Confirm 401 on bogus token (uvicorn really enforces the dep)."""
    with _client() as c:
        r = c.get(
            f"{live_server}/api/v1/projects/anything",
            headers={"Authorization": "Bearer not-a-real-key"},
        )
        assert r.status_code == 401
