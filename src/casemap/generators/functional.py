"""Functional generator - LLM-driven enrichment of structural cases."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, Field

from casemap._internal.logger import get_logger
from casemap.llm.provider import LLMProvider
from casemap.models.endpoint import Endpoint
from casemap.models.testcase import TestCase

_log = get_logger("generators.functional")
T = TypeVar("T", bound=BaseModel)


class _EnrichedCase(BaseModel):
    """LLM-returned enrichment for one test case."""

    id: str
    title: str
    description: str = ""


class _EnrichmentResult(BaseModel):
    cases: list[_EnrichedCase] = Field(default_factory=list)


class FunctionalGenerator:
    """Use LLM to rewrite structural cases into business-language descriptions."""

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider

    async def enhance(
        self,
        endpoints: list[Endpoint],
        structural_cases: list[TestCase],
    ) -> list[TestCase]:
        if self.provider is None or not structural_cases:
            return structural_cases
        try:
            prompt = self._build_prompt(endpoints, structural_cases)
            result = await self.provider.complete_json(
                prompt,
                schema=_EnrichmentResult,
            )
        except Exception as e:  # noqa: BLE001 - we MUST NOT break on LLM failure
            _log.warning("LLM enrichment failed (%s); using structural cases", e)
            return structural_cases
        # Merge: LLM rewrites title/description by ID
        enriched_map = {c.id: c for c in result.cases}
        merged: list[TestCase] = []
        for orig in structural_cases:
            if orig.id in enriched_map:
                enr = enriched_map[orig.id]
                merged.append(
                    orig.model_copy(
                        update={
                            "title": enr.title.strip() or orig.title,
                            "description": enr.description.strip() or orig.description,
                        }
                    )
                )
            else:
                merged.append(orig)
        return merged

    def _build_prompt(
        self,
        endpoints: list[Endpoint],
        structural_cases: list[TestCase],
    ) -> str:
        ep_summary = [
            {"method": str(e.method), "path": e.path, "summary": e.summary} for e in endpoints
        ]
        case_list = [
            {"id": c.id, "type": c.type.value, "current_title": c.title} for c in structural_cases
        ]
        return json.dumps(
            {
                "interfaces": ep_summary,
                "structural_cases": case_list,
                "task": (
                    "Rewrite each case's title and description in pure business language. "
                    "Return a JSON object with field 'cases' = list of {id, title, description}."
                ),
            },
            ensure_ascii=False,
        )
