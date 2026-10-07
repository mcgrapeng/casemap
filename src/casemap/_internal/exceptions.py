"""Custom exceptions for casemap."""

from __future__ import annotations


class CasemapError(Exception):
    """Base exception for all casemap errors."""


class ParseError(CasemapError):
    """Failed to parse input document."""


class GenerationError(CasemapError):
    """Failed to generate test cases."""


class RenderError(CasemapError):
    """Failed to render output."""


class LLMError(CasemapError):
    """LLM provider returned an error."""
