"""End-to-end integration: petstore spec → pipeline with mock LLM → TestGraph.

Uses a FakeProvider that conforms to the LLMProvider Protocol. No real
network calls — runs in CI without any API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from casemap.generators.pipeline import GenerationPipeline
from casemap.llm.provider import LLMProvider
from casemap.parsers.openapi import OpenAPIParser

SPEC = Path(__file__).parent.parent / "fixtures" / "petstore_swagger.json"


class FakeProvider:
    """Conforms to LLMProvider Protocol; returns empty enrichment."""

    name = "fake"

    async def complete(self, prompt, *, system=None):
        return '{"cases":[]}'

    async def complete_json(self, prompt, *, schema, system=None):
        return schema.model_validate({"cases": []})


@pytest.mark.asyncio
async def test_pipeline_with_fake_llm():
    spec = json.loads(SPEC.read_text())
    endpoints = OpenAPIParser().parse(spec)
    pipeline = GenerationPipeline(llm=FakeProvider())  # type: ignore[arg-type]
    g = await pipeline.run_async(endpoints, title="Petstore")
    # Fake LLM returns no enrichments → structural only
    assert g.title == "Petstore"
    assert len(g.nodes) > 0
    # Sanity: the fake really did conform to the protocol
    assert isinstance(pipeline.llm, LLMProvider)
