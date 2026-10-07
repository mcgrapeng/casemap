"""Endpoint data models - the unified representation of API endpoints.

All parsers (OpenAPI, Postman, apifox) must produce Endpoint objects with this schema.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HttpMethod(str, Enum):
    """HTTP methods recognized by casemap."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


# ponytail: Literal over Enum for Parameter.location keeps this field a plain
# string (matches OpenAPI's canonical set), so JSON round-trips stay clean and
# parsers can pass raw strings without coercion. Invalid locations fail at model
# validation rather than silently passing bad strings downstream.
ParameterLocation = Literal["path", "query", "header", "body", "formData"]


class Parameter(BaseModel):
    """A single API parameter (query, path, header, body, form)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    location: ParameterLocation
    type: str  # simplified type: "string" | "integer" | "number" | "boolean" | "array" | "object"
    required: bool = False
    description: str = ""
    example: Any | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    # constraints carries: {"min": ..., "max": ..., "pattern": ..., "enum": [...], "format": ...}


class Response(BaseModel):
    """A documented response."""

    model_config = ConfigDict(extra="forbid")

    status_code: str  # "200", "4XX", "default" etc.
    description: str = ""


class Endpoint(BaseModel):
    """A unified API endpoint representation."""

    model_config = ConfigDict(extra="forbid")

    path: str
    method: HttpMethod
    summary: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    operation_id: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    request_body: Parameter | None = None
    responses: list[Response] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
    # raw keeps the original spec entry for round-trip and debugging.
