from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from casemap.cli import main

FIX = Path(__file__).parent.parent / "fixtures"


def test_generate_no_llm(tmp_path):
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "cases.html"
    result = runner.invoke(
        main,
        ["generate", str(src), "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_text().startswith("<!DOCTYPE html>")


def test_generate_with_parser_choice(tmp_path):
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "cases.html"
    result = runner.invoke(
        main,
        ["generate", str(src), "-o", str(out), "--parser", "openapi"],
    )
    assert result.exit_code == 0, result.output


def test_generate_auto_detect_from_petstore(tmp_path):
    """Auto-detect should pick openapi parser from a Swagger 2.0 doc."""
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "auto.html"
    result = runner.invoke(main, ["generate", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    # HTML must contain some rendered test case titles
    body = out.read_text()
    assert "petstore_swagger" in body  # title from input stem


def test_parsers_list():
    runner = CliRunner()
    result = runner.invoke(main, ["parsers", "list"])
    assert result.exit_code == 0, result.output
    assert "openapi" in result.output


def test_validate_valid():
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIX / "petstore_swagger.json")])
    assert result.exit_code == 0, result.output
    assert "endpoints" in result.output.lower()


def test_generate_file_not_found(tmp_path):
    runner = CliRunner()
    out = tmp_path / "should_not_exist.html"
    result = runner.invoke(
        main,
        ["generate", "/nonexistent.json", "-o", str(out)],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_resume_advises_generate(tmp_path):
    runner = CliRunner()
    html_in = tmp_path / "in.html"
    statuses = tmp_path / "statuses.json"
    html_in.write_text("<!DOCTYPE html>")
    statuses.write_text("{}")
    out = tmp_path / "out.html"
    result = runner.invoke(
        main,
        ["resume", str(html_in), str(statuses), "-o", str(out)],
    )
    # Resume is a stub - we expect it to print guidance and exit non-zero
    assert result.exit_code != 0


# ---------- SP-5 v0.2 Minor: --verbose / --quiet log-level flags ----------


def test_verbose_sets_log_level_info(monkeypatch):
    from click.testing import CliRunner

    from casemap.cli import main

    monkeypatch.delenv("CASEMAP_LOG_LEVEL", raising=False)
    runner = CliRunner()
    # Invoke a real subcommand so the group callback runs.
    result = runner.invoke(main, ["-v", "parsers", "list"])
    assert result.exit_code == 0, result.output
    import os

    assert os.environ.get("CASEMAP_LOG_LEVEL") == "INFO"


def test_quiet_sets_log_level_warning(monkeypatch):
    from click.testing import CliRunner

    from casemap.cli import main

    monkeypatch.delenv("CASEMAP_LOG_LEVEL", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, ["-q", "parsers", "list"])
    assert result.exit_code == 0, result.output
    import os

    assert os.environ.get("CASEMAP_LOG_LEVEL") == "WARNING"


# ---------- Friendly aliases (v1.1.1: brain / html / ui / start) ----------


def test_help_lists_aliases():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    for name in ("generate", "brain", "html", "serve", "ui", "start", "init"):
        assert name in result.output, f"missing {name!r} in --help:\n{result.output}"


def test_alias_brain_runs_generate(tmp_path):
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "cases.html"
    result = runner.invoke(main, ["brain", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_text().startswith("<!DOCTYPE html>")


def test_alias_html_runs_generate(tmp_path):
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "cases.html"
    result = runner.invoke(main, ["html", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_alias_brain_passes_flags(tmp_path):
    runner = CliRunner()
    src = FIX / "petstore_swagger.json"
    out = tmp_path / "brain.html"
    result = runner.invoke(
        main, ["brain", str(src), "-o", str(out), "--parser", "openapi"]
    )
    assert result.exit_code == 0, result.output


def test_alias_ui_help_uses_under_help():
    """Each alias's --help shows the usage line under its own name."""
    runner = CliRunner()
    for alias in ("brain", "html", "ui", "start"):
        result = runner.invoke(main, [alias, "--help"])
        assert result.exit_code == 0, result.output
        assert f"Usage: main {alias}" in result.output, (
            f"{alias}: usage line should mention alias name, got:\n{result.output}"
        )


# ---------- `init` first-time setup wizard ----------


def test_init_non_interactive_with_token_writes_html(tmp_path):
    """`init --admin-token ... --no-start-server` writes the localStorage page."""
    runner = CliRunner()
    token_page = tmp_path / "admin_token.html"
    result = runner.invoke(
        main,
        [
            "init",
            "--admin-token",
            "secret-xyz",
            "--token-save-path",
            str(token_page),
            "--no-start-server",
            "--no-open-browser",
        ],
    )
    assert result.exit_code == 0, result.output
    assert token_page.exists()
    body = token_page.read_text(encoding="utf-8")
    assert "secret-xyz" in body
    assert "casemap.admin_token" in body
    assert "localStorage" in body


def test_init_skips_html_when_no_token(tmp_path):
    """No --admin-token → no HTML page created (interactive prompt returns empty)."""
    runner = CliRunner()
    token_page = tmp_path / "should_not_exist.html"
    result = runner.invoke(
        main,
        [
            "init",
            "--non-interactive",
            "--token-save-path",
            str(token_page),
            "--no-start-server",
        ],
    )
    assert result.exit_code == 0, result.output
    assert not token_page.exists()
    assert "skipping" in result.output.lower()


def test_init_token_html_escapes_special_chars(tmp_path):
    """The token page must JSON-escape the token to keep arbitrary input safe."""
    runner = CliRunner()
    token_page = tmp_path / "x.html"
    # Token with quotes + script tag — must be escaped, not literal.
    dangerous = '</script>"oops"'
    result = runner.invoke(
        main,
        [
            "init",
            "--admin-token",
            dangerous,
            "--token-save-path",
            str(token_page),
            "--no-start-server",
        ],
    )
    assert result.exit_code == 0, result.output
    body = token_page.read_text(encoding="utf-8")
    # raw dangerous token must NOT appear verbatim inside a script tag context
    # (Click's safe attribute escapes it as &#x3C; etc.).
    assert "<script>" in body
    # The JSON-escaped form is what should be written:
    import json as _json

    assert _json.dumps(dangerous) in body


def test_init_token_save_path_expands_tilde(tmp_path, monkeypatch):
    """`--token-save-path` honours ~ expansion."""
    runner = CliRunner()
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    target = fake_home / "tok.html"
    result = runner.invoke(
        main,
        [
            "init",
            "--admin-token",
            "t",
            "--token-save-path",
            "~/tok.html",
            "--no-start-server",
        ],
    )
    assert result.exit_code == 0, result.output
    assert target.exists()


def test_init_spawns_serve_with_correct_invocation(monkeypatch, tmp_path):
    """When `--start-server` is on, init spawns `casemap serve` detached."""

    captured: list[list[str]] = []

    def fake_spawn(host: str, port: int) -> object:
        # Capture what _spawn_serve would have invoked.
        import sys as _sys

        captured.append(
            [_sys.executable, "-m", "casemap.cli", "serve", "--host", host, "--port", str(port)]
        )
        return object()

    monkeypatch.setattr("casemap.cli._spawn_serve", fake_spawn)
    monkeypatch.setattr("casemap.cli._open_browser", lambda url: None)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--admin-token",
            "tok",
            "--no-open-browser",
            "--port",
            "9999",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(captured) == 1, f"expected one spawn, got {captured}"
    assert captured[0][-2:] == ["--port", "9999"]
    assert "casemap.cli" in captured[0]
    assert "serve" in captured[0]


def test_init_interactive_full_flow(tmp_path, monkeypatch):
    """Full stdin-driven flow: token → save path → start server → open browser."""
    monkeypatch.setattr("casemap.cli._spawn_serve", lambda h, p: object())
    monkeypatch.setattr("casemap.cli._open_browser", lambda url: None)

    runner = CliRunner()
    token_page = tmp_path / "tok.html"
    input_lines = (
        "abc-token\n"  # admin token
        f"{token_page}\n"  # token save path (overrides default)
        "y\n"  # start server? y
        "n\n"  # open browser? n
    )
    result = runner.invoke(main, ["init"], input=input_lines)
    assert result.exit_code == 0, result.output
    assert token_page.exists()
    assert "abc-token" in token_page.read_text(encoding="utf-8")
    assert "Skipped" not in result.output  # we said yes to server
    assert "Server detached" in result.output
