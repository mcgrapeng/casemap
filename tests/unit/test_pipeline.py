from __future__ import annotations

from typing import TypeVar

import pytest
from pydantic import BaseModel

from casemap.generators.functional import FunctionalGenerator
from casemap.generators.pipeline import GenerationPipeline, run_pipeline
from casemap.generators.structural import StructuralGenerator
from casemap.llm.config import LLMConfig  # noqa: F401
from casemap.llm.provider import LLMProvider
from casemap.models.endpoint import Endpoint, HttpMethod, Response
from casemap.models.testcase import CaseType, TestCase, TestStatus  # noqa: F401

T = TypeVar("T", bound=BaseModel)


class _EnrichedCase(BaseModel):
    id: str
    title: str
    description: str = ""


class StubProvider:
    """Returns a fixed list of enriched cases (simulates LLM)."""

    name = "stub"

    def __init__(self, enriched: list[_EnrichedCase] | None = None, fail: bool = False):
        self._enriched = enriched or []
        self._fail = fail
        self.calls = 0

    async def complete(self, prompt, *, system=None):
        self.calls += 1
        if self._fail:
            raise RuntimeError("simulated LLM failure")
        # Return JSON that the functional generator will parse
        import json

        return json.dumps([c.model_dump() for c in self._enriched])

    async def complete_json(self, prompt, *, schema, system=None):
        assert isinstance(self, LLMProvider)
        return schema.model_validate({"cases": [c.model_dump() for c in self._enriched]})


def _endpoint() -> Endpoint:
    return Endpoint(path="/users", method=HttpMethod.POST, responses=[Response(status_code="200")])


def _structural_cases(ep: Endpoint) -> list[TestCase]:
    return StructuralGenerator().generate([ep])


class TestFunctionalGenerator:
    @pytest.mark.asyncio
    async def test_no_provider_returns_input(self):
        gen = FunctionalGenerator(provider=None)
        cases = _structural_cases(_endpoint())
        out = await gen.enhance([_endpoint()], cases)
        assert out == cases

    @pytest.mark.asyncio
    async def test_provider_failure_falls_back_to_structural(self):
        ep = _endpoint()
        cases = _structural_cases(ep)
        gen = FunctionalGenerator(provider=StubProvider(fail=True))
        out = await gen.enhance([ep], cases)
        # Failure must not raise - we return structural unchanged
        assert out == cases

    @pytest.mark.asyncio
    async def test_enriches_titles(self):
        ep = _endpoint()
        cases = _structural_cases(ep)
        enriched = [
            _EnrichedCase(id=cases[0].id, title="业务语言标题：创建用户") for c in cases[:1]
        ]
        gen = FunctionalGenerator(provider=StubProvider(enriched=enriched))
        out = await gen.enhance([ep], cases)
        assert "业务语言标题" in out[0].title

    @pytest.mark.asyncio
    async def test_sanitizes_dangerous_chars_in_enriched_text(self):
        """SP-5 v0.2 defense-in-depth: LLM-returned text with angle brackets or
        control chars must NOT flow into the rendered HTML even if the XSS fix
        were ever regressed. Strip them on receipt.
        """
        ep = _endpoint()
        cases = _structural_cases(ep)
        poisoned_title = "<script>alert(1)</script>正常标题"
        poisoned_desc = "A\x00B\x07C 描述 with <img src=x onerror=alert(2)>"
        enriched = [_EnrichedCase(id=cases[0].id, title=poisoned_title, description=poisoned_desc)]
        gen = FunctionalGenerator(provider=StubProvider(enriched=enriched))
        out = await gen.enhance([ep], cases)
        # No angle brackets, no control chars in the output
        assert "<" not in out[0].title and ">" not in out[0].title
        assert "<" not in out[0].description and ">" not in out[0].description
        assert "\x00" not in out[0].description and "\x07" not in out[0].description
        # The benign text survives
        assert "正常标题" in out[0].title
        assert "描述" in out[0].description


class TestGenerationPipeline:
    def test_structural_only(self):
        ep = _endpoint()
        pipeline = GenerationPipeline(llm=None)
        g = pipeline.run([ep], title="t")
        assert g.title == "t"
        assert len(g.nodes) == len(_structural_cases(ep))

    @pytest.mark.asyncio
    async def test_with_llm(self):
        ep = _endpoint()
        cases = _structural_cases(ep)
        enriched = [_EnrichedCase(id=cases[0].id, title="业务标题")]
        pipeline = GenerationPipeline(llm=StubProvider(enriched=enriched))
        g = await pipeline.run_async([ep], title="t")
        assert "业务标题" in g.nodes[0].case.title


# ---------- SP-5 v0.2 Important #1: run_pipeline must not crash inside a loop ----------


class TestRunPipeline:
    def test_no_llm_sync(self):
        ep = _endpoint()
        g = run_pipeline([ep])
        assert g.nodes

    def test_inside_running_loop_raises_clear_error(self):
        """asyncio.run() crashes with 'asyncio.run() cannot be called from a
        running event loop'. run_pipeline() must give the user a usable hint
        instead of the bare RuntimeError - it should point at `await
        pipeline.run_async(...)` as the fix.
        """
        import asyncio

        async def _inside() -> None:
            with pytest.raises(RuntimeError, match="run_async"):
                run_pipeline([_endpoint()], llm=StubProvider())

        asyncio.run(_inside())

    def test_edges_group_by_endpoint_ref(self):
        """Edges must connect consecutive cases that share the same endpoint_ref."""
        ep = _endpoint()
        g = run_pipeline([ep], title="t")
        # All structural cases for /users POST share the same endpoint_ref.
        ref = f"{ep.method} {ep.path}"
        edge_pairs = {(e.source, e.target) for e in g.edges}
        same_ref_ids = [n.id for n in g.nodes if n.case.endpoint_ref == ref]
        # Every consecutive pair must be in the edge set
        for a, b in zip(same_ref_ids, same_ref_ids[1:]):
            assert (a, b) in edge_pairs, f"missing edge ({a} -> {b})"
