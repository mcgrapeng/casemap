"""casemap command-line interface."""

from __future__ import annotations

import asyncio
import json
import os
import sys
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


@click.group()
def main() -> None:
    """casemap - 功能测试用例图管理系统."""


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


if __name__ == "__main__":
    main()
