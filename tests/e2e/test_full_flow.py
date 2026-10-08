"""End-to-end Playwright test: admin token → create project → upload spec → brain map.

Boots a real casemap server in a temp DB, drives the web UI from cold start through
"mark case as passed" + progress verification, and captures 9 full-page screenshots
into ``docs/screenshots/`` for the user-guide docs.

Self-contained: no env admin tokens required, no shared DB.

Marked ``@pytest.mark.slow`` so default CI runs skip it; opt in via
``pytest -m slow`` or nightly cron.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
PETSTORE = ROOT / "examples" / "petstore_swagger.json"
SCREENSHOTS = ROOT / "docs" / "screenshots"
DEFAULT_PORT = 8766  # one above the smoke default so parallel runs don't collide


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(base: str, proc: subprocess.Popen, deadline_s: float = 30.0) -> None:
    import httpx

    deadline = time.time() + deadline_s
    last_err: Exception | None = None
    with httpx.Client(timeout=1.0, trust_env=False) as probe:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"server process exited (rc={proc.returncode}) before becoming ready"
                )
            try:
                if probe.get(f"{base}/openapi.json").status_code == 200:
                    return
            except Exception as e:  # noqa: BLE001
                last_err = e
            time.sleep(0.2)
    raise RuntimeError(f"server never became ready at {base}: {last_err}")


@pytest.fixture(scope="module")
def running_server(tmp_path_factory):
    """Boot a one-shot casemap server on a temp DB; yield (base_url, admin_token)."""
    port = _free_port()
    db_dir = tmp_path_factory.mktemp("casemap-e2e")
    db_path = db_dir / "e2e.db"
    db_url = f"sqlite:///{db_path}"
    admin_token = f"test-admin-{uuid.uuid4().hex[:16]}"

    env = os.environ.copy()
    env["CASEMAP_SERVER_DB_URL"] = db_url
    env["CASEMAP_SERVER_ADMIN_TOKEN"] = admin_token

    base = f"http://127.0.0.1:{port}"
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

    try:
        _wait_ready(base, proc)
        yield base, admin_token
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass
        log_file.close()


def _shoot(page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    out = SCREENSHOTS / name
    page.screenshot(path=str(out), full_page=True)
    print(f"[e2e] shot {out.relative_to(ROOT)}", flush=True)


@pytest.mark.slow
def test_full_flow(running_server) -> None:
    """Drive the complete UI happy path and capture 9 documentation screenshots."""
    from playwright.sync_api import expect, sync_playwright

    base_url, admin_token = running_server

    # Don't override PLAYWRIGHT_BROWSERS_PATH — Playwright's OS default
    # is correct everywhere: ~/Library/Caches/ms-playwright on macOS,
    # ~/.cache/ms-playwright on Linux. CI uses the default, the dev's
    # Mac uses the default, no hardcoded paths to keep in sync.
    project_name = f"e2e-petstore-{uuid.uuid4().hex[:8]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            color_scheme="light",
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.on("console", lambda msg: print(f"[browser:{msg.type}] {msg.text}", flush=True))
        page.on("pageerror", lambda err: print(f"[browser:error] {err}", flush=True))
        page.on(
            "requestfailed",
            lambda req: print(f"[browser:reqfail] {req.method} {req.url} -> {req.failure}", flush=True),
        )
        page.on(
            "response",
            lambda r: (
                print(f"[browser:resp] {r.status} {r.request.method} {r.url}", flush=True)
                if r.status >= 400 or "/api/" in r.url
                else None
            ),
        )

        # ── 1. Open /web/ ────────────────────────────────────────────────
        page.goto(f"{base_url}/web/", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Projects")).to_be_visible()
        _shoot(page, "01-homepage.png")

        # ── 2. Set admin token via password input + Enter ────────────────
        page.get_by_label("Admin token", exact=True).fill(admin_token)
        page.get_by_role("button", name="保存").click()
        expect(page.get_by_text("已配置。仅用于列出与创建项目。")).to_be_visible()
        _shoot(page, "02-admin-token-set.png")

        # ── 3. Click "New Project" tab ───────────────────────────────────
        page.get_by_role("button", name="Create new project").click()
        expect(page.get_by_role("heading", name="New Project")).to_be_visible()

        # ── 4. Fill name, click "Create" ─────────────────────────────────
        page.get_by_label("Name").fill(project_name)
        _shoot(page, "03-new-project-form.png")
        page.get_by_role("button", name="Create project").click()

        # ── 5. Verify "Save your API key" dialog appears ─────────────────
        api_key_dialog = page.get_by_role("dialog", name="Save your API key")
        expect(api_key_dialog).to_be_visible()

        # ── 6. Click "Copy" — verify clipboard matches the revealed key ─
        # Reveal first so the underlying text node shows the real key.
        page.get_by_role("button", name="Reveal key").click()
        api_key_code = page.get_by_label("Project API key")
        expect(api_key_code).to_be_visible()
        api_key_text = api_key_code.inner_text().strip()
        # casemap keys are secrets.token_urlsafe(32) → ~43 chars, URL-safe base64.
        assert len(api_key_text) >= 40, (
            f"API key should be at least 40 chars (got {len(api_key_text)})"
        )
        page.get_by_role("button", name="Copy key to clipboard").click()
        expect(page.get_by_role("button", name="Copy key to clipboard")).to_contain_text(
            "Copied"
        )
        clipboard_value = page.evaluate("navigator.clipboard.readText()")
        assert len(clipboard_value) >= 40, (
            f"clipboard key should be at least 40 chars (got {len(clipboard_value)})"
        )
        assert clipboard_value == api_key_text, "clipboard should match displayed key"
        _shoot(page, "04-api-key-dialog.png")

        # ── 7. Click "Continue to project" ───────────────────────────────
        page.get_by_role("button", name="Continue to project").click()

        # ── 8. Verify URL matches /projects/{uuid} pattern ───────────────
        expect(page.get_by_role("heading", name=project_name)).to_be_visible()
        url = page.url
        # SPA uses BrowserRouter at root → /projects/{uuid}
        assert "/projects/" in url
        tail = url.split("/projects/")[-1].rstrip("/")
        assert len(tail) == 36 and tail.count("-") == 4, (
            f"project id tail should look like a uuid, got: {tail!r}"
        )

        # ── 9. Verify project name shows in header ───────────────────────
        expect(page.get_by_role("heading", name=project_name)).to_be_visible()

        # ── 10. Verify progress panel shows 0/0 (0%) ─────────────────────
        progress_region = page.get_by_role("region", name="Test progress")
        expect(progress_region).to_be_visible()
        expect(progress_region).to_contain_text("0/0 (0%)")
        _shoot(page, "05-project-empty.png")

        # ── 11. Upload petstore spec via file input ──────────────────────
        # The visible "Upload Spec" button triggers this hidden input.
        # Ponytail: set_input_files() works directly on hidden file inputs
        # without needing the button click — Playwright bypasses the picker.
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(PETSTORE))

        # ── 12. Wait for upload to complete + brain map to render ────────
        brain_map_svg = page.locator('[data-testid="brain-map-svg"]')
        expect(brain_map_svg).to_be_visible(timeout=30_000)

        # ── 13. Verify brain map appears (SVG element present) ──────────
        # Wait for the graph to populate (after upload, the graph hook refetches)
        # The SVG renders immediately but nodes only appear after data arrives.
        expect(page.locator('[data-node="true"]').first).to_be_visible(timeout=30_000)

        # ── 14. Verify case count is 15 ──────────────────────────────────
        expect(page.get_by_role("heading", name=project_name)).to_be_visible()
        # Progress should now show 0/15 (0%) — pending is 15, passed=0.
        expect(progress_region).to_contain_text("0/15")
        case_node_count = page.locator('[data-node="true"]').count()
        assert case_node_count == 15, f"expected 15 case nodes, got {case_node_count}"
        _shoot(page, "07-brain-map.png")

        # Also capture the upload-spec moment for docs/06 — scroll to show
        # the upload controls above the freshly-generated brain map.
        upload_btn = page.get_by_role("button", name="Upload Spec").nth(1)  # 0=hidden input, 1=visible button
        upload_btn.scroll_into_view_if_needed()
        _shoot(page, "06-upload-spec.png")

        # ── 15. Click a case node → verify detail panel shows ───────────
        first_node = page.locator('[data-node="true"]').first
        first_node.click()
        case_detail = page.get_by_role("complementary", name="Case details")
        expect(case_detail).to_be_visible()
        _shoot(page, "08-case-detail.png")

        # ── 16. Mark case as "passed" → verify color changes ────────────
        page.get_by_role("button", name="Mark as 通过").click()
        page.get_by_role("button", name="保存").click()
        # Wait for the green stroke to appear on the first node.
        # stroke-status-passed is a CSS class; check it via the class list.
        expect(first_node.locator("rect").first).to_have_class(
            __import__("re").compile(r"stroke-status-passed"),
            timeout=10_000,
        )

        # ── 17. Verify progress now shows 1/15 ───────────────────────────
        expect(progress_region).to_contain_text("1/15")
        _shoot(page, "09-status-marked.png")

        browser.close()
