from __future__ import annotations

from typing import TypeVar

import pytest
from pydantic import BaseModel

from casemap.generators.functional import FunctionalGenerator
from casemap.generators.pipeline import GenerationPipeline
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
