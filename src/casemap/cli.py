"""casemap command-line interface."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

import click

from casemap._internal.exceptions import ParseError
from casemap._internal.logger import get_logger
from casemap.generators.pipeline import GenerationPipeline
from casemap.llm.config import LLMConfig
from casemap.llm.openai_compat import OpenAICompatProvider
from casemap.parsers import all_parsers
from casemap.parsers.base import ParserRegistry
from casemap.renderers.html_self import HTMLSelfRenderer

_log = get_logger("cli")


def _apply_log_flags(verbose: bool, quiet: bool) -> None:
    """Translate CLI verbosity flags into CASEMAP_LOG_LEVEL.

    Set BEFORE get_logger() is invoked by any subcommand, so the new level
    takes effect on every logger in the casemap namespace. Last-write-wins
    if both flags are given (it's a CLI misuse, not worth erroring).
    """
    if verbose:
        os.environ["CASEMAP_LOG_LEVEL"] = "INFO"
    elif quiet:
        os.environ["CASEMAP_LOG_LEVEL"] = "WARNING"


@click.group()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable INFO-level logging (sets CASEMAP_LOG_LEVEL=INFO)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Restrict logging to WARNING and above (sets CASEMAP_LOG_LEVEL=WARNING)",
)
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """casemap - 功能测试用例图管理系统."""
    _apply_log_flags(verbose, quiet)
    ctx.ensure_object(dict)


@main.command()
@click.argument("input", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path(), help="Output HTML path")
@click.option("--parser", default=None, help="Parser name (default: auto-detect)")
@click.option("--llm", is_flag=True, help="Enable LLM enrichment")
@click.option(
    "--llm-provider",
    default=None,
    help="LLM provider (openai/anthropic/ollama, default: from CASEMAP_LLM_PROVIDER or 'openai')",
)
@click.option(
    "--model",
    default=None,
    help="LLM model name (default: from CASEMAP_LLM_MODEL or 'gpt-4o-mini')",
)
def generate(
    input: str,
    output: str,
    parser: str | None,
    llm: bool,
    llm_provider: str | None,
    model: str | None,
) -> None:
    """Generate a test case brain map from an interface list."""
    try:
        raw = _read_input(input)
    except ParseError as e:
        click.echo(f"Invalid: {e}", err=True)
        sys.exit(1)
    if parser:
        p = ParserRegistry.get(parser, default=None)
        if p is None:
            click.echo(f"Parser not registered: {parser!r}", err=True)
            sys.exit(1)
        endpoints = p.parse(raw)
    else:
        endpoints = ParserRegistry.parse_auto(raw)
    if not endpoints:
        click.echo("No endpoints parsed. Check your input file.", err=True)
        sys.exit(1)

    provider = None
    if llm:
        cfg = LLMConfig(
            provider=llm_provider or os.environ.get("CASEMAP_LLM_PROVIDER", "openai"),
            model=model or os.environ.get("CASEMAP_LLM_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("CASEMAP_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("CASEMAP_LLM_BASE_URL"),
        )
        if not cfg.api_key:
            click.echo("LLM enabled but no API key found. Set CASEMAP_LLM_API_KEY.", err=True)
            sys.exit(1)
        provider = OpenAICompatProvider(cfg)
    pipeline = GenerationPipeline(llm=provider)
    if provider is not None:
        graph = asyncio.run(pipeline.run_async(endpoints, title=Path(input).stem))
    else:
        graph = pipeline.run(endpoints, title=Path(input).stem)
    html = HTMLSelfRenderer().render(graph)
    # ponytail: temp-and-rename prevents corrupt HTML when CLI is killed mid-write.
    out_path = Path(output)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, out_path)
    click.echo(f"Wrote {output} ({len(graph.nodes)} cases from {len(endpoints)} endpoints)")


@main.command()
@click.argument("input_html", type=click.Path(exists=True))
@click.argument("statuses_json", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path())
def resume(input_html: str, statuses_json: str, output: str) -> None:
    """Re-render an HTML with externally-supplied statuses."""
    json.loads(Path(statuses_json).read_text())  # validate it's parseable
    click.echo(
        "resume is not yet implemented (no HTML→spec roundtrip). "
        "Re-run `casemap generate` on the original spec instead.",
        err=True,
    )
    sys.exit(1)


@main.group()
def parsers() -> None:
    """Inspect available parsers."""


@parsers.command("list")
def parsers_list() -> None:
    """List all registered parsers."""
    for p in all_parsers():
        click.echo(f"  {p.name} (v{p.version})")


@main.command()
@click.argument("input", type=click.Path(exists=True))
def validate(input: str) -> None:
    """Validate an interface document without generating."""
    try:
        raw = _read_input(input)
    except ParseError as e:
        click.echo(f"Invalid: {e}", err=True)
        sys.exit(1)
    try:
        endpoints = ParserRegistry.parse_auto(raw)
    except ParseError as e:
        click.echo(f"Invalid: {e}", err=True)
        sys.exit(1)
    click.echo(f"Parsed {len(endpoints)} endpoints")
    for ep in endpoints[:5]:
        click.echo(f"  - {ep.method} {ep.path}")


_MAX_INPUT_BYTES = 100 * 1024 * 1024  # 100 MB


def _read_input(path: str) -> dict[str, Any]:
    p = Path(path)
    size = p.stat().st_size
    if size > _MAX_INPUT_BYTES:
        raise ParseError(
            f"Input file too large: {size} bytes (max {_MAX_INPUT_BYTES:,}). "
            "Split your spec or contact support."
        )
    text = p.read_text(encoding="utf-8")
    result: dict[str, Any] = json.loads(text)
    return result


@main.command()
@click.option("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
@click.option("--port", default=8765, type=int, help="Bind port (default: 8765)")
@click.option(
    "--db",
    "db_url",
    default=None,
    help="SQLAlchemy DB URL (default: $CASEMAP_SERVER_DB_URL or sqlite:///./casemap.db)",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Auto-reload on file changes (dev mode)",
)
def serve(host: str, port: int, db_url: str | None, reload: bool) -> None:
    """Run the casemap REST server (FastAPI + SQLite)."""
    # ponytail: importing uvicorn + casemap.server here (not at module top)
    # so `casemap generate` doesn't pay the FastAPI import cost.
    import uvicorn  # noqa: PLC0415

    url = db_url or os.environ.get("CASEMAP_SERVER_DB_URL", "sqlite:///./casemap.db")
    os.environ["CASEMAP_SERVER_DB_URL"] = url
    os.environ["CASEMAP_SERVER_HOST"] = host
    os.environ["CASEMAP_SERVER_PORT"] = str(port)
    click.echo(f"casemap server starting at http://{host}:{port}  db={url}")
    from casemap.server.app import app  # noqa: PLC0415

    uvicorn.run(app, host=host, port=port, reload=reload)


# ponytail: aliases registered after the underlying commands so the original
# callbacks stay the single point of behavior. Same Command object, two names.
main.add_command(generate, name="brain")
main.add_command(generate, name="html")
main.add_command(serve, name="ui")
main.add_command(serve, name="start")


_DEFAULT_TOKEN_PAGE = "~/.casemap/admin_token.html"
_TOKEN_LOCALSTORAGE_KEY = "casemap.admin_token"


def _token_save_html(token: str) -> str:
    """HTML page that writes *token* to localStorage on open.

    The casemap frontend reads `casemap.admin_token` from localStorage on its
    admin-gated endpoints; opening this file in a browser stores it there so
    the user doesn't have to type it into the UI every session.
    """
    payload = json.dumps(token)
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\"><title>Save casemap admin token</title>"
        "</head><body>\n"
        f"<script>localStorage.setItem({json.dumps(_TOKEN_LOCALSTORAGE_KEY)}, {payload});"
        "document.body.textContent='Saved admin token to localStorage. You can close this tab.';"
        "</script>\n"
        "</body></html>\n"
    )


def _spawn_serve(host: str, port: int) -> subprocess.Popen[bytes]:
    """Spawn `casemap serve` detached; returns the Popen handle."""
    return subprocess.Popen(  # noqa: S603  (intentional detached background spawn)
        [sys.executable, "-m", "casemap.cli", "serve", "--host", host, "--port", str(port)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_browser(url: str) -> None:
    webbrowser.open(url)


@main.command()
@click.option("--admin-token", default=None, help="Admin token (prompted if omitted)")
@click.option(
    "--token-save-path",
    default=_DEFAULT_TOKEN_PAGE,
    type=click.Path(),
    show_default=True,
    help="Where to write the localStorage-setter HTML page",
)
@click.option(
    "--start-server/--no-start-server",
    default=True,
    help="Spawn the casemap server in the background after setup",
)
@click.option(
    "--open-browser/--no-open-browser",
    default=True,
    help="Open the UI in a browser after the server starts",
)
@click.option("--host", default="127.0.0.1", show_default=True, help="Server bind host")
@click.option("--port", default=8765, type=int, show_default=True, help="Server bind port")
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Skip prompts (use only the supplied flags / defaults)",
)
def init(
    admin_token: str | None,
    token_save_path: str,
    start_server: bool,
    open_browser: bool,
    host: str,
    port: int,
    non_interactive: bool,
) -> None:
    """Interactive first-time setup wizard."""
    click.echo("Welcome to casemap — let's get you set up.\n")

    # --- Admin token -------------------------------------------------------
    token_from_prompt = False
    if admin_token is None and not non_interactive:
        typed = click.prompt(
            "What's your admin token? (press Enter to skip)",
            default="",
            show_default=False,
        )
        stripped = typed.strip()
        if stripped:
            admin_token = stripped
            token_from_prompt = True

    if admin_token:
        # If the token came from a prompt, also confirm where to save it.
        # When the user supplies both --admin-token and --token-save-path via
        # the CLI we skip this and trust the supplied values.
        if token_from_prompt and not non_interactive:
            token_save_path = click.prompt(
                "Where should we save your admin token?",
                default=token_save_path,
                show_default=False,
            )
        save_path = Path(token_save_path).expanduser()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(_token_save_html(admin_token), encoding="utf-8")
        click.echo(f"\nWrote admin-token page → {save_path}")
        click.echo(
            "Open that file in your browser once to write the token to localStorage "
            "(key: casemap.admin_token)."
        )
    else:
        click.echo("No admin token provided — skipping localStorage save.")

    # --- Server ------------------------------------------------------------
    if start_server and not non_interactive and not click.confirm(
        "Start the server now?", default=True
    ):
        start_server = False

    if start_server:
        url = f"http://{host}:{port}"
        click.echo(f"\nStarting casemap server at {url} (background) ...")
        try:
            _spawn_serve(host, port)
        except OSError as e:
            click.echo(f"Failed to spawn server: {e}", err=True)
            sys.exit(1)
        click.echo(f"Server detached. Browse to: {url}")

        if open_browser and not non_interactive and click.confirm(
            "Open browser to UI?", default=True
        ):
            _open_browser(url)
    else:
        click.echo("\nSkipped starting server. Run `casemap serve` when ready.")


if __name__ == "__main__":
    main()
