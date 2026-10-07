"""LLM configuration - strict single-model (per spec requirement #11)."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LLMConfig(BaseModel):
    """Single-model LLM configuration.

    Per spec #11, casemap REQUIRES exactly one model. Multi-model lists are
    intentionally not supported — casemap assumes a single fixed deployment
    and would otherwise need fan-out / fallback logic that adds complexity
    without a real use case.

    Note: the plan's draft monkey-patched ``model_fields["model"].annotation``
    at import time. We avoid that fragility by declaring the field as ``str``
    and adding an explicit ``field_validator`` that produces a clear error
    message (pydantic's default coercion error would still reject a list, but
    the validator copy points users at spec #11 instead of at pydantic).
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    provider: str  # "openai" | "anthropic" | "ollama" | any OpenAI-compatible
    model: str  # exactly one model name (spec #11)
    api_key: str | None = None
    base_url: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    temperature: float = 0.2

    @field_validator("model", mode="before")
    @classmethod
    def _check_model_is_string(cls, v: object) -> object:
        if not isinstance(v, str):
            raise ValueError("spec #11: casemap supports exactly one model (string)")
        return v

    @model_validator(mode="before")
    @classmethod
    def _apply_env_defaults(cls, data: object) -> object:
        # Runs on the raw input dict before field validation, so we can fill
        # in missing api_key from env without wrestling with validate_default.
        if not isinstance(data, dict):
            return data
        if not data.get("api_key"):
            env = os.environ.get("OPENAI_API_KEY") or os.environ.get("CASEMAP_LLM_API_KEY")
            if env:
                data["api_key"] = env
        return data

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Build config from environment variables (CASEMAP_LLM_*)."""
        return cls(
            provider=os.environ.get("CASEMAP_LLM_PROVIDER", "openai"),
            model=os.environ.get("CASEMAP_LLM_MODEL", "gpt-4o-mini"),
            base_url=os.environ.get("CASEMAP_LLM_BASE_URL"),
        )
