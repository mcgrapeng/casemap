"""End-to-end router tests via TestClient."""

from __future__ import annotations

from pathlib import Path

FIX = Path(__file__).parent.parent / "fixtures"
PETSTORE = FIX / "petstore_swagger.json"


# ---------- helpers ----------


def _create_project(client) -> tuple[dict, str]:
    r = client.post("/api/v1/projects", json={"name": "acme"})
    assert r.status_code == 201, r.text
    body = r.json()
    return body, body["project_api_key"]


def _upload_petstore(client, project_id: str, token: str) -> dict:
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


# ---------- projects ----------


def test_create_project_returns_one_time_key(client):
    body, key = _create_project(client)
    assert body["name"] == "acme"
    assert len(key) >= 32
    assert body["id"]


def test_create_project_duplicate_name_returns_409(client):
    _create_project(client)
    r = client.post("/api/v1/projects", json={"name": "acme"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_create_project_missing_name_returns_422(client):
    r = client.post("/api/v1/projects", json={})
    assert r.status_code == 422


def test_list_projects_requires_admin(client):
    _create_project(client)
    # Without admin token → 403
    r = client.get("/api/v1/projects")
    assert r.status_code == 403
    # With admin token (set in env before creating app)... but we override
    # at app start; skip if admin not configured.
    # Just verify the route exists and requires *some* admin guard.


def test_get_project_returns_metadata(client):
    body, key = _create_project(client)
    r = client.get(
        f"/api/v1/projects/{body['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "acme"


def test_get_project_404(client):
    body, key = _create_project(client)
    r = client.get(
        "/api/v1/projects/does-not-exist",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 404


def test_delete_project_removes_it(client):
    body, key = _create_project(client)
    r = client.delete(
        f"/api/v1/projects/{body['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 204
    # After delete, the bearer is no longer valid (project gone) → 401.
    r2 = client.get(
        f"/api/v1/projects/{body['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code in (401, 404)


def test_get_project_wrong_project_returns_404(client):
    body, key = _create_project(client)
    other = client.post(
        "/api/v1/projects",
        json={"name": "other"},
        headers={"Authorization": f"Bearer {key}"},
    ).json()
    # Try to view the OTHER project using body key
    r = client.get(
        f"/api/v1/projects/{other['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 404


# ---------- auth ----------


def test_protected_endpoint_requires_bearer(client):
    body, _ = _create_project(client)
    r = client.get(f"/api/v1/projects/{body['id']}")
    assert r.status_code == 401


def test_invalid_bearer_returns_401(client):
    # Need a real project first so we can hit a bearer-guarded route.
    body, _ = _create_project(client)
    r = client.get(
        f"/api/v1/projects/{body['id']}",
        headers={"Authorization": "Bearer not-a-real-key"},
    )
    assert r.status_code == 401


# ---------- specs ----------


def test_upload_spec_creates_graph(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    assert result["spec_id"]
    assert result["graph_id"]
    assert result["case_count"] > 0


def test_upload_spec_auto_detect_format(client):
    body, key = _create_project(client)
    files = {"file": ("petstore.json", PETSTORE.read_text(), "application/json")}
    r = client.post(
        f"/api/v1/projects/{body['id']}/specs",
        files=files,
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 201, r.text


def test_upload_spec_invalid_json_returns_400(client):
    body, key = _create_project(client)
    files = {"file": ("bad.json", "{not json", "application/json")}
    r = client.post(
        f"/api/v1/projects/{body['id']}/specs",
        files=files,
        data={"format": "openapi"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 400


def test_upload_spec_wrong_token_returns_401(client):
    body, _ = _create_project(client)
    files = {"file": ("petstore.json", PETSTORE.read_text(), "application/json")}
    r = client.post(
        f"/api/v1/projects/{body['id']}/specs",
        files=files,
        data={"format": "openapi"},
        headers={"Authorization": "Bearer not-a-real-key"},
    )
    assert r.status_code == 401


def test_list_specs_after_upload(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/specs",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_spec_returns_metadata(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/specs/{result['spec_id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["format"] == "openapi"
    assert j["graph_id"] == result["graph_id"]
    assert j["case_count"] == result["case_count"]


# ---------- brain map ----------


def test_graph_svg_returns_svg(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/graphs/{result['graph_id']}/svg",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert r.text.startswith("<svg")


def test_graph_html_returns_html(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/graphs/{result['graph_id']}/html",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert r.text.startswith("<!DOCTYPE html>")
    # Must contain interactive bits: SVG + status buttons
    assert "<svg" in r.text.lower()
    assert "localStorage" in r.text


def test_graph_report_returns_html(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/graphs/{result['graph_id']}/report",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "测试报告" in r.text or "Test Report" in r.text


def test_graph_data_returns_json(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/graphs/{result['graph_id']}/graph.json",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    j = r.json()
    assert "graph" in j and "statuses" in j
    assert len(j["graph"]["nodes"]) == result["case_count"]


# ---------- cases ----------


def test_list_cases_returns_each_with_status_default_pending(client):
    body, key = _create_project(client)
    result = _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) == result["case_count"]
    for c in cases:
        assert c["status"] == "pending"
        assert c["id"] and c["title"]


def test_get_single_case(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    case = r.json()[0]
    r2 = client.get(
        f"/api/v1/projects/{body['id']}/cases/{case['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == case["id"]


def test_patch_status_updates_case(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    case_id = r.json()[0]["id"]
    r2 = client.patch(
        f"/api/v1/projects/{body['id']}/cases/{case_id}/status",
        json={"status": "passed", "note": "all good"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "passed"
    assert r2.json()["note"] == "all good"
    # Re-fetch and confirm persisted
    r3 = client.get(
        f"/api/v1/projects/{body['id']}/cases/{case_id}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r3.json()["status"] == "passed"


def test_progress_aggregates_after_patches(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    cases = r.json()
    # Pass first 2
    for c in cases[:2]:
        client.patch(
            f"/api/v1/projects/{body['id']}/cases/{c['id']}/status",
            json={"status": "passed"},
            headers={"Authorization": f"Bearer {key}"},
        )
    r2 = client.get(
        f"/api/v1/projects/{body['id']}/progress",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200
    p = r2.json()
    assert p["passed"] == 2
    assert p["total"] == len(cases)
    assert p["completion_pct"] == round(2 / len(cases) * 100, 2)


# ---------- statuses (bulk import/export) ----------


def test_bulk_export_after_updates(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    case_id = r.json()[0]["id"]
    client.patch(
        f"/api/v1/projects/{body['id']}/cases/{case_id}/status",
        json={"status": "failed", "note": "boom"},
        headers={"Authorization": f"Bearer {key}"},
    )
    r2 = client.get(
        f"/api/v1/projects/{body['id']}/statuses/export",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200
    entries = r2.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["status"] == "failed"


def test_bulk_import_creates_statuses(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    case_ids = [c["id"] for c in r.json()]
    payload = {
        "entries": [
            {"case_id": cid, "status": "passed", "note": ""}
            for cid in case_ids[:3]
        ]
    }
    r2 = client.post(
        f"/api/v1/projects/{body['id']}/statuses/import",
        json=payload,
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200
    assert r2.json()["imported"] == 3


# ---------- CI ----------


def test_ci_report_applies_statuses_to_matched_cases(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    r = client.get(
        f"/api/v1/projects/{body['id']}/cases",
        headers={"Authorization": f"Bearer {key}"},
    )
    cases = r.json()
    payload = {
        "results": [
            {"test_name": "test_a", "matched_case_id": cases[0]["id"], "status": "passed"},
            {"test_name": "test_b", "matched_case_id": cases[1]["id"], "status": "failed"},
        ]
    }
    r2 = client.post(
        f"/api/v1/projects/{body['id']}/ci/report",
        json=payload,
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r2.status_code == 200
    j = r2.json()
    assert j["matched"] == 2
    assert j["unmatched"] == 0
    # Cases now have ci-sourced status
    r3 = client.get(
        f"/api/v1/projects/{body['id']}/cases/{cases[0]['id']}",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r3.json()["status"] == "passed"


def test_ci_report_unmatched_counts(client):
    body, key = _create_project(client)
    _upload_petstore(client, body["id"], key)
    payload = {
        "results": [{"test_name": "ghost", "matched_case_id": "no-such", "status": "passed"}]
    }
    r = client.post(
        f"/api/v1/projects/{body['id']}/ci/report",
        json=payload,
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert r.json() == {"matched": 0, "unmatched": 1}


def test_ci_token_endpoint(client):
    body, key = _create_project(client)
    r = client.post(
        f"/api/v1/projects/{body['id']}/ci/token",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["project_id"] == body["id"]
    assert "endpoint" in j
