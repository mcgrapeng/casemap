"""Tests for HTMLSelfRenderer (Task 13, post P0 fix).

CRITICAL: HTML must be 100% self-contained (no Mermaid CDN, no http/https
outside the SVG xmlns). All interactivity must come from inline JS + inline SVG.

P0 #2 — no external script tags
P0 #3 — status export / import mechanism for PM cross-browser visibility
"""

from __future__ import annotations

import re
from pathlib import Path

from casemap.models.graph import TestGraph, TestNode
from casemap.models.testcase import CaseType, TestCase, TestStatus
from casemap.renderers.html_self import HTMLSelfRenderer


def _case(
    i: int = 1,
    *,
    type_: CaseType = CaseType.POSITIVE,
    status: TestStatus = TestStatus.PENDING,
    tags: list[str] | None = None,
    title: str | None = None,
    endpoint_ref: str | None = None,
) -> TestCase:
    return TestCase(
        id=f"c{i}",
        type=type_,
        title=title or f"用例{i}",
        status=status,
        tags=tags or [],
        endpoint_ref=endpoint_ref,
    )


def _graph(*nodes: TestNode, title: str = "t") -> TestGraph:
    return TestGraph(title=title, nodes=list(nodes))


# ---------- structure ----------


def test_minimal_html_has_doctype():
    g = _graph(TestNode(id="a", case=_case()))
    html = HTMLSelfRenderer().render(g)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_contains_graph_payload():
    g = _graph(
        TestNode(id="abc123", case=TestCase(id="abc123", type=CaseType.POSITIVE, title="登录")),
        title="My Project",
    )
    html = HTMLSelfRenderer().render(g)
    assert "My Project" in html
    assert "登录" in html
    assert "abc123" in html


def test_responsive_meta_viewport():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "viewport" in html
    assert "width=device-width" in html


# ---------- status UI ----------


def test_contains_status_buttons():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "✅" in html or "通过" in html
    assert "❌" in html or "失败" in html


def test_contains_localstorage_script():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "localStorage" in html


def test_with_existing_statuses():
    g = _graph(TestNode(id="a", case=_case()))
    statuses = {"a": {"status": "passed", "note": "first-try"}}
    html = HTMLSelfRenderer().render(g, statuses=statuses)
    # initial statuses serialized into the page
    assert "passed" in html
    assert "first-try" in html
    # the case id appears somewhere (in JS map)
    assert '"a"' in html or "'a'" in html


# ---------- P0 #2: no external script tags ----------


def test_no_external_script_tags():
    """Critical: HTML must be 100% self-contained (no CDN)."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "googleapis.com" not in html
    # No <script src="..."> tags at all (every script must be inline)
    assert re.search(r"<script[^>]+src=", html) is None, "external <script src=> found"


def test_no_http_https_outside_svg_xmlns():
    """The only http URL allowed is the SVG xmlns declaration."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    stripped = html.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "http://" not in stripped, f"found http:// in {html[:300]!r}"
    assert "https://" not in stripped, f"found https:// in {html[:300]!r}"


# ---------- P0 #3: status export / import ----------


def test_contains_export_status_button():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "导出进度" in html or "export-status" in html.lower()


def test_contains_import_button():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "导入进度" in html or "import" in html.lower()
    # file input for upload
    assert "<input" in html and 'type="file"' in html


def test_contains_dirty_tracker_javascript():
    """JS must set casemap_dirty in sessionStorage on status change."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "casemap_dirty" in html


def test_export_filename_uses_today_date():
    """The downloaded status file is `casemap-status-YYYY-MM-DD.json`."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    # filename pattern is set by JS at click-time, but the prefix should be in the JS
    assert "casemap-status-" in html


# ---------- SVG payload comes from SVGRenderer ----------


def test_embeds_svg_in_body():
    """SVG is inlined in the body — no Mermaid, no fetch."""
    g = _graph(
        TestNode(id="u1", case=TestCase(id="u1", type=CaseType.POSITIVE, title="登录")),
    )
    html = HTMLSelfRenderer().render(g)
    assert "<svg" in html
    assert "</svg>" in html
    # Each node wrapped in <a data-case-id="..."> by the SVG renderer
    assert 'data-case-id="u1"' in html


def test_status_color_reflected_in_embedded_svg():
    """When statuses passed in, the embedded SVG should reflect them."""
    g = _graph(
        TestNode(
            id="p",
            case=TestCase(id="p", type=CaseType.POSITIVE, title="p", status=TestStatus.PASSED),
        ),
        TestNode(
            id="f",
            case=TestCase(id="f", type=CaseType.NEGATIVE, title="f", status=TestStatus.FAILED),
        ),
    )
    html = HTMLSelfRenderer().render(
        g, statuses={"p": {"status": "passed"}, "f": {"status": "failed"}}
    )
    # PASSED fill is #d1fae5; FAILED fill is #fee2e2 (per Task 11 SVG renderer)
    assert "#d1fae5" in html
    assert "#fee2e2" in html


# ---------- design polish ----------


def test_has_progress_bar():
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "progress" in html.lower()
    assert "progress-bar" in html or "progressbar" in html.lower()


def test_has_dark_mode_css():
    """CSS must include dark mode via prefers-color-scheme."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "prefers-color-scheme" in html


def test_has_mobile_breakpoint():
    """CSS must collapse to single column at <=768px."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    assert "768" in html
    assert "@media" in html


def test_case_node_click_delegation_js():
    """JS must register a click listener for .case-node elements (event delegation)."""
    g = _graph()
    html = HTMLSelfRenderer().render(g)
    # one place uses addEventListener for .case-node OR querySelectorAll('.case-node')
    assert "case-node" in html
    assert "addEventListener" in html


# ---------- SP-5 Critical #1: XSS via </script> in JSON-in-script ----------


def test_xss_script_breakout_blocked_in_payload():
    """A case title containing </script>...<script> must NOT appear literally
    in the JSON payload inside the <script> block — only the escaped <\\/ form.
    """
    evil_title = "x</script><script>alert(1)</script>"
    g = _graph(
        TestNode(
            id="evil",
            case=TestCase(id="evil", type=CaseType.POSITIVE, title=evil_title),
        )
    )
    html = HTMLSelfRenderer().render(g)
    # The JSON payload is the substring between the script-element-opening
    # tag for INITIAL_STATUSES_JS and its legitimate closing </script> tag.
    # Find the boundaries precisely: the payload lives between
    # `<script>` (the one immediately preceding window.__INITIAL_STATUSES__)
    # and the FIRST </script> after that.
    start = html.find("window.__INITIAL_STATUSES__")
    assert start != -1
    # Walk back to the <script> tag that opens this block
    script_open = html.rfind("<script>", 0, start)
    assert script_open != -1
    # Find the legitimate closing tag of this <script> element
    script_close = html.find("</script>", start)
    assert script_close != -1
    payload_segment = html[script_open + len("<script>"):script_close]
    # The literal '</script>' must not appear inside the JSON payload
    assert "</script>" not in payload_segment, (
        f"XSS: literal </script> leaked into JSON payload: {payload_segment!r}"
    )
    # But the escape <\\/script> must be present (proves the payload is safe-encoded)
    assert "<\\/script>" in payload_segment, (
        f"expected escaped form in payload, got: {payload_segment[:200]!r}"
    )


# ---------- SP-5 Important #1: string.Template placeholder conflict ----------


def test_dollar_in_case_title_does_not_corrupt_payload():
    """A case title containing $cases_json must not be substituted by Template.

    string.Template.substitute treats $name as a placeholder. If the title is
    `$cases_json`, the substitute call would either raise KeyError (unknown
    identifier in the JSON) or silently replace the JSON. With str.replace
    semantics, the literal $cases_json should survive verbatim.
    """
    g = _graph(
        TestNode(
            id="d1",
            case=TestCase(
                id="d1",
                type=CaseType.POSITIVE,
                title="test $cases_json and $statuses_json $",
            ),
        )
    )
    html = HTMLSelfRenderer().render(g)  # should not raise
    assert "$cases_json" in html
    assert "$statuses_json" in html


# ---------- SP-5 Important #3: atomic HTML output write ----------


def test_generate_writes_atomically_via_tmp(tmp_path, monkeypatch):
    """The CLI should write to .tmp then os.replace, not direct write_text.

    Verified by inspecting that no leftover .tmp file remains after success
    and that the final output file is intact.
    """
    # ponytail: re-register parsers. test_parsers_base.setup_function clears
    # ParserRegistry._parsers between tests and never re-registers the
    # real parsers; an earlier file leaves the registry empty. Force a
    # re-import via importlib so the top-level register() calls re-run.
    import importlib

    import casemap.parsers as _parsers
    import casemap.parsers.apifox as _apifox
    import casemap.parsers.openapi as _openapi
    import casemap.parsers.postman as _postman

    importlib.reload(_openapi)
    importlib.reload(_postman)
    importlib.reload(_apifox)
    importlib.reload(_parsers)

    from click.testing import CliRunner

    from casemap.cli import main

    runner = CliRunner()
    src = Path(__file__).parent.parent / "fixtures" / "petstore_swagger.json"
    out = tmp_path / "atomic.html"
    result = runner.invoke(main, ["generate", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    # No leftover .tmp file next to the output
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == [], f"leftover tmp files: {leftover}"
    # Output should be complete (starts with doctype)
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


# ---------- SP-5 Important #9: unbounded input file read ----------


def test_generate_rejects_oversized_input(tmp_path, monkeypatch):
    """CLI must reject input files above the size cap before reading them all.

    We lower the cap to 100 bytes via monkeypatch so the test stays fast and
    doesn't actually allocate 100MB on disk.
    """
    from click.testing import CliRunner

    import casemap.cli as cli_mod
    from casemap.cli import main

    monkeypatch.setattr(cli_mod, "_MAX_INPUT_BYTES", 100)

    runner = CliRunner()
    src = tmp_path / "huge.json"
    # Content > 100 bytes (pad with whitespace in a JSON comment-like field)
    src.write_text('{"openapi": "3.0.0", "info": {"title": "' + ("x" * 200) + '", "version": "1"}}')

    out = tmp_path / "out.html"
    result = runner.invoke(main, ["generate", str(src), "-o", str(out)])
    assert result.exit_code != 0
    assert "too large" in result.output.lower()
    assert not out.exists()


def test_read_input_accepts_small_and_rejects_oversized(tmp_path, monkeypatch):
    """Unit-test the size guard on _read_input directly.

    Lower the cap to 100 bytes so we don't have to allocate a real 100MB file.
    """
    import casemap.cli as cli_mod
    from casemap._internal.exceptions import ParseError

    monkeypatch.setattr(cli_mod, "_MAX_INPUT_BYTES", 100)

    # Small file under cap → succeeds
    small = tmp_path / "small.json"
    small.write_text("{}")
    assert cli_mod._read_input(str(small)) == {}

    # File above cap → raises ParseError BEFORE reading
    big = tmp_path / "big.json"
    big.write_text("a" * 200)
    try:
        cli_mod._read_input(str(big))
    except ParseError as e:
        assert "too large" in str(e).lower()
    else:
        raise AssertionError("expected ParseError for over-cap file")
