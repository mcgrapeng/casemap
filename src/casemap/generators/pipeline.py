"""Generation pipeline - orchestrates structural + functional layers."""

from __future__ import annotations

import asyncio
from typing import Any

from casemap._internal.logger import get_logger
from casemap.generators.functional import FunctionalGenerator
from casemap.generators.structural import StructuralGenerator
from casemap.llm.provider import LLMProvider
from casemap.models.endpoint import Endpoint
from casemap.models.graph import Edge, TestGraph, TestNode
from casemap.models.testcase import TestCase, TestStatus

_log = get_logger("generators.pipeline")


class GenerationPipeline:
    """Top-level orchestrator. Use this from CLI / external code."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        structural: StructuralGenerator | None = None,
        functional: FunctionalGenerator | None = None,
    ):
        self.llm = llm
        self.structural = structural or StructuralGenerator()
        self.functional = functional or FunctionalGenerator(llm)

    def run(
        self,
        endpoints: list[Endpoint],
        *,
        title: str = "Test Graph",
        statuses: dict[str, str] | None = None,
    ) -> TestGraph:
        """Synchronous entry point (no LLM)."""
        cases = self.structural.generate(endpoints)
        cases = self._apply_statuses(cases, statuses)
        return self._build_graph(title, cases, endpoints)

    async def run_async(
        self,
        endpoints: list[Endpoint],
        *,
        title: str = "Test Graph",
        statuses: dict[str, str] | None = None,
    ) -> TestGraph:
        """Async entry point (supports LLM enrichment)."""
        cases = self.structural.generate(endpoints)
        cases = await self.functional.enhance(endpoints, cases)
        cases = self._apply_statuses(cases, statuses)
        return self._build_graph(title, cases, endpoints)

    @staticmethod
    def _apply_statuses(
        cases: list[TestCase], statuses: dict[str, str] | None
    ) -> list[TestCase]:
        if not statuses:
            return cases
        out: list[TestCase] = []
        for c in cases:
            s = statuses.get(c.id)
            if s and s in TestStatus._value2member_map_:
                out.append(c.model_copy(update={"status": TestStatus(s)}))
            else:
                out.append(c)
        return out

    @staticmethod
    def _build_graph(
        title: str,
        cases: list[TestCase],
        endpoints: list[Endpoint],
    ) -> TestGraph:
        nodes = [TestNode(id=c.id, case=c) for c in cases]
        # Simple edges: group cases by endpoint_ref, connect in order
        edges: list[Edge] = []
        for ep in endpoints:
            ref = f"{ep.method} {ep.path}"
            ep_cases = [n for n in nodes if n.case.endpoint_ref == ref]
            for i in range(len(ep_cases) - 1):
                edges.append(Edge(source=ep_cases[i].id, target=ep_cases[i + 1].id))
        return TestGraph(
            title=title,
            nodes=nodes,
            edges=edges,
            metadata={"endpoint_count": str(len(endpoints)), "case_count": str(len(cases))},
        )


def run_pipeline(
    endpoints: list[Endpoint],
    llm: LLMProvider | None = None,
    **kwargs: Any,
) -> TestGraph:
    """Convenience function for the common case."""
    pipeline = GenerationPipeline(llm=llm)
    if llm is None:
        return pipeline.run(endpoints, **kwargs)
    return asyncio.run(pipeline.run_async(endpoints, **kwargs))
