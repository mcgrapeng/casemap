"""End-to-end smoke script for casemap server.

Runnable as a shell-style script — NOT a pytest test. Drives the same pipeline
the user-facing flow uses (create project → upload spec → fetch HTML/SVG → patch
status → fetch progress) against a live uvicorn instance.

Usage:
    python tests/server/test_e2e.py

Exits 0 on success, 1 on any failure. Prints a one-line-per-step transcript so
the run is greppable in CI logs.
"""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
PETSTORE = ROOT / "examples" / "petstore_swagger.json"
DEFAULT_PORT = 8765


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(base: str, proc: subprocess.Popen, deadline_s: float = 30.0) -> None:
    deadline = time.time() + deadline_s
    last_err: Exception | None = None
    # ponytail: trust_env=False — some shells export HTTP_PROXY/HTTPS_PROXY by
    # default and httpx honors them, sending our localhost call to a corporate
    # proxy that returns 502. The smoke client (and now the wait probe) opt out.
    with httpx.Client(timeout=1.0, trust_env=False) as probe:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"server process exited (rc={proc.returncode}) before becoming ready"
                )
            try:
                r = probe.get(f"{base}/openapi.json")
                if r.status_code == 200:
                    return
            except Exception as e:  # noqa: BLE001
                last_err = e
            time.sleep(0.2)
    raise RuntimeError(f"server never became ready at {base}: {last_err}")


def main() -> int:
    if not PETSTORE.exists():
        print(f"FAIL: petstore fixture missing at {PETSTORE}", file=sys.stderr)
        return 1

    port = int(os.environ.get("CASEMAP_E2E_PORT", DEFAULT_PORT))
    db_dir = Path(tempfile.mkdtemp(prefix="casemap-e2e-"))
    db_path = db_dir / "e2e.db"
    db_url = f"sqlite:///{db_path}"

    env = os.environ.copy()
    env["CASEMAP_SERVER_DB_URL"] = db_url

    print(f"[e2e] starting casemap serve on :{port} (db={db_path})")
    log_path = db_dir / "server.log"
    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "casemap",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--db",
            db_url,
        ],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    base = f"http://127.0.0.1:{port}"
    rc = 1
    try:
        _wait_ready(base, proc)
        client = httpx.Client(timeout=10.0, trust_env=False)
        try:
            rc = _run_pipeline(base, client)
        finally:
            client.close()
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        log_file.close()
        if rc != 0:
            print(f"[e2e] server log retained: {log_path}", file=sys.stderr)
        shutil.rmtree(db_dir, ignore_errors=True)
    return rc


def _run_pipeline(base: str, client: httpx.Client) -> int:
    api = f"{base}/api/v1"

    # 1. Create two projects so we exercise the multi-project PK path too.
    r = client.post(
        f"{api}/projects", json={"name": "e2e_a", "llm_provider": "openai", "llm_model": "gpt-4o-mini"}
    )
    assert r.status_code == 201, f"create A failed: {r.status_code} {r.text}"
    a = r.json()
    pa, ka = a["id"], a["project_api_key"]
    print(f"[e2e] created project A {pa}")

    r = client.post(
        f"{api}/projects", json={"name": "e2e_b", "llm_provider": "openai", "llm_model": "gpt-4o-mini"}
    )
    assert r.status_code == 201, f"create B failed: {r.status_code} {r.text}"
    b = r.json()
    pb, kb = b["id"], b["project_api_key"]
    print(f"[e2e] created project B {pb}")

    # 2. Upload the same spec to both projects.
    spec = PETSTORE.read_bytes()
    r = client.post(
        f"{api}/projects/{pa}/specs",
        files={"file": ("petstore_swagger.json", spec, "application/json")},
        data={"format": "openapi"},
        headers={"Authorization": f"Bearer {ka}"},
    )
    assert r.status_code == 201, f"upload A failed: {r.status_code} {r.text}"
    ga = r.json()["graph_id"]
    print(f"[e2e] uploaded spec to A → graph {ga}")

    r = client.post(
        f"{api}/projects/{pb}/specs",
        files={"file": ("petstore_swagger.json", spec, "application/json")},
        data={"format": "openapi"},
        headers={"Authorization": f"Bearer {kb}"},
    )
    assert r.status_code == 201, f"upload B failed: {r.status_code} {r.text}"
    gb = r.json()["graph_id"]
    print(f"[e2e] uploaded spec to B → graph {gb}")

    # 3. Fetch HTML + SVG.
    r = client.get(
        f"{api}/projects/{pa}/graphs/{ga}/html",
        headers={"Authorization": f"Bearer {ka}"},
    )
    assert r.status_code == 200, f"html A failed: {r.status_code} {r.text}"
    assert "<svg" in r.text.lower(), "html missing inline SVG"
    print(f"[e2e] fetched HTML ({len(r.text)} bytes)")

    r = client.get(
        f"{api}/projects/{pa}/graphs/{ga}/svg",
        headers={"Authorization": f"Bearer {ka}"},
    )
    assert r.status_code == 200, f"svg A failed: {r.status_code} {r.text}"
    assert r.text.startswith("<svg"), "svg body did not start with <svg"
    print(f"[e2e] fetched SVG ({len(r.text)} bytes)")

    # 4. PATCH a status. Use the public stable_id, not the row PK.
    cases = client.get(
        f"{api}/projects/{pa}/cases",
        headers={"Authorization": f"Bearer {ka}"},
    ).json()
    assert cases, "no cases returned for project A"
    cid = cases[0]["id"]
    r = client.patch(
        f"{api}/projects/{pa}/cases/{cid}/status",
        json={"status": "passed", "note": "e2e", "source": "human"},
        headers={"Authorization": f"Bearer {ka}"},
    )
    assert r.status_code == 200, f"patch failed: {r.status_code} {r.text}"
    assert r.json()["status"] == "passed"
    print(f"[e2e] patched case {cid[:12]}… → passed")

    # 5. Progress should reflect exactly one passed in A, zero in B.
    pa_prog = client.get(
        f"{api}/projects/{pa}/progress",
        headers={"Authorization": f"Bearer {ka}"},
    ).json()
    pb_prog = client.get(
        f"{api}/projects/{pb}/progress",
        headers={"Authorization": f"Bearer {kb}"},
    ).json()
    assert pa_prog["passed"] == 1, f"A progress wrong: {pa_prog}"
    assert pb_prog["passed"] == 0, f"B progress wrong: {pb_prog}"
    print(
        f"[e2e] progress  A={pa_prog['passed']}/{pa_prog['total']}  "
        f"B={pb_prog['passed']}/{pb_prog['total']} (independent ✓)"
    )

    print("[e2e] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
