"""WebSocket real-time status sync tests (SP-4)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

FIX = Path(__file__).parent.parent / "fixtures"
PETSTORE = FIX / "petstore_swagger.json"


# ---------- helpers ----------


def _create_project(client: TestClient, name: str = "acme") -> tuple[dict, str]:
    r = client.post("/api/v1/projects", json={"name": name})
    assert r.status_code == 201, r.text
    body = r.json()
    return body, body["project_api_key"]


def _upload_petstore(client: TestClient, project_id: str, token: str) -> dict:
    files = {"file": ("petstore.json", PETSTORE.read_text(), "application/json")}
    data = {"format": "openapi"}
    r = client.post(
        f"/api/v1/projects/{project_id}/specs",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _first_case_id(client: TestClient, project_id: str, token: str) -> str:
    r = client.get(
        f"/api/v1/projects/{project_id}/cases",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    cases = r.json()
    assert cases, "no cases in fresh project"
    return cases[0]["id"]


def _expect_no_message(ws, timeout_s: float = 0.5) -> None:
    """Assert that `ws` does NOT receive any JSON message within `timeout_s`.

    Starlette's TestClient WebSocket has no native timeout on receive, so we
    run a receiver thread and join with a timeout. If anything arrives, fail.
    """
    received: list[object] = []

    def _receive() -> None:
        try:
            received.append(ws.receive_json())
        except Exception:  # noqa: BLE001
            pass

    t = threading.Thread(target=_receive, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        # Force-close so the test doesn't leak the thread.
        try:
            ws.close(1000)
        except Exception:  # noqa: BLE001
            pass
        return
    pytest.fail(f"expected no message but got: {received}")


# ---------- WS endpoint ----------


def test_ws_rejects_missing_token(client: TestClient) -> None:
    body, _ = _create_project(client)
    with pytest.raises(WebSocketDisconnect) as ei:
        with client.websocket_connect(f"/api/v1/projects/{body['id']}/ws"):
            pass
    # Close code 1008 = policy violation, what we send on auth failure.
    assert ei.value.code == 1008


def test_ws_rejects_invalid_token(client: TestClient) -> None:
    body, _ = _create_project(client)
    with pytest.raises(WebSocketDisconnect) as ei:
        with client.websocket_connect(
            f"/api/v1/projects/{body['id']}/ws?token=not-a-real-key"
        ):
            pass
    assert ei.value.code == 1008


def test_ws_accepts_valid_token(client: TestClient) -> None:
    body, key = _create_project(client)
    with client.websocket_connect(
        f"/api/v1/projects/{body['id']}/ws?token={key}"
    ) as ws:
        ws.send_text("hello")  # ignored by server, but must not disconnect us
        # No broadcast yet — close cleanly.
    # If we got here without exception, accept+ignore worked.


def test_ws_broadcasts_status_change(client: TestClient) -> None:
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    case_id = _first_case_id(client, body["id"], key)

    with client.websocket_connect(
        f"/api/v1/projects/{body['id']}/ws?token={key}"
    ) as ws:
        # Trigger a status change on the server (via REST).
        client.patch(
            f"/api/v1/projects/{body['id']}/cases/{case_id}/status",
            json={"status": "passed", "note": "all good", "source": "human"},
            headers={"Authorization": f"Bearer {key}"},
        )
        msg = ws.receive_json()
        assert msg["type"] == "status_changed"
        assert msg["case_id"] == case_id
        assert msg["status"] == "passed"
        assert msg["note"] == "all good"
        assert msg["source"] == "human"
        assert msg["updated_at"]


def test_ws_broadcasts_bulk_import(client: TestClient) -> None:
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    case_ids = [
        c["id"]
        for c in client.get(
            f"/api/v1/projects/{body['id']}/cases",
            headers={"Authorization": f"Bearer {key}"},
        ).json()
    ][:2]

    with client.websocket_connect(
        f"/api/v1/projects/{body['id']}/ws?token={key}"
    ) as ws:
        client.post(
            f"/api/v1/projects/{body['id']}/statuses/import",
            json={
                "entries": [
                    {"case_id": cid, "status": "failed", "note": "imported"}
                    for cid in case_ids
                ]
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        seen: set[str] = set()
        # Two broadcasts expected — drain until we have both case_ids.
        for _ in range(len(case_ids)):
            msg = ws.receive_json()
            assert msg["type"] == "status_changed"
            seen.add(msg["case_id"])
            assert msg["source"] == "import"
        assert seen == set(case_ids)


def test_ws_broadcasts_ci_report(client: TestClient) -> None:
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    cases = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    ).json()

    with client.websocket_connect(
        f"/api/v1/projects/{body['id']}/ws?token={key}"
    ) as ws:
        client.post(
            f"/api/v1/projects/{body['id']}/ci/report",
            json={
                "results": [
                    {"test_name": "t", "matched_case_id": cases[0]["id"], "status": "passed"}
                ]
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        msg = ws.receive_json()
        assert msg["type"] == "status_changed"
        assert msg["case_id"] == cases[0]["id"]
        assert msg["source"] == "ci"


def test_ws_does_not_cross_projects(client: TestClient) -> None:
    """A patch on project B must NOT broadcast on project A's WS."""
    body_a, key_a = _create_project(client, name="alpha")
    body_b, key_b = _create_project(client, name="beta")
    _upload_petstore(client, body_a["id"], key_a)
    _upload_petstore(client, body_b["id"], key_b)
    case_b = _first_case_id(client, body_b["id"], key_b)

    with client.websocket_connect(
        f"/api/v1/projects/{body_a['id']}/ws?token={key_a}"
    ) as ws:
        client.patch(
            f"/api/v1/projects/{body_b['id']}/cases/{case_b}/status",
            json={"status": "passed", "note": "x"},
            headers={"Authorization": f"Bearer {key_b}"},
        )
        # Nothing should arrive on A's WS within a short timeout.
        _expect_no_message(ws, timeout_s=0.3)


def test_ws_disconnect_clears_queue(client: TestClient) -> None:
    """After a client disconnects, no further broadcasts are sent to it."""
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    case_id = _first_case_id(client, body["id"], key)

    with client.websocket_connect(
        f"/api/v1/projects/{body['id']}/ws?token={key}"
    ) as ws:
        ws.receive_json  # establish connection

    # Disconnected. Next patch must not raise (no stale connection in queue).
    r = client.patch(
        f"/api/v1/projects/{body['id']}/cases/{case_id}/status",
        json={"status": "passed", "note": "after-disconnect"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200, r.text
