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
