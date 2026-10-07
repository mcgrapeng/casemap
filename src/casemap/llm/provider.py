"""LLM provider protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    """Provider that completes prompts and returns structured output.

    Implementations:
        - OpenAICompatProvider (default; covers OpenAI/Anthropic/Ollama/vLLM/...)
        - Custom providers for any LLM SDK not compatible with OpenAI's protocol
    """

    name: str

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Free-form text completion."""
        ...

    async def complete_json(
        self,
        prompt: str,
        *,
        schema: type[T],
        system: str | None = None,
    ) -> T:
        """Structured completion validated against a pydantic schema."""
        ...
