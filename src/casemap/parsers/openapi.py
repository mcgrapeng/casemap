"""OpenAPI / Swagger parser.

Supports Swagger 2.0 and OpenAPI 3.0/3.1. Uses prance to resolve $ref and
normalize the spec into a consistent shape, then maps it to Endpoint objects.
"""

from __future__ import annotations

import json
from typing import Any

from prance import ResolvingParser  # type: ignore[import-untyped]

from casemap._internal.exceptions import ParseError
from casemap._internal.logger import get_logger
from casemap.models.endpoint import Endpoint, HttpMethod, Parameter, Response
from casemap.parsers.base import ParserRegistry

_log = get_logger("parsers.openapi")

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
_VALID_LOCATIONS = {"path", "query", "header", "formData"}
_CONSTRAINT_KEYS = {
    "minimum",
    "maximum",
    "minLength",
    "maxLength",
    "pattern",
    "enum",
    "format",
    "minItems",
    "maxItems",
    "default",
}
_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "file": "string",
}


def _coerce_spec(data: dict[str, Any] | str | bytes) -> dict[str, Any]:
    """Decode str/bytes → dict, pass dict through."""
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ParseError(f"Failed to decode OpenAPI spec bytes: {e}") from e
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ParseError(f"Failed to parse OpenAPI spec as JSON: {e}") from e
    if not isinstance(data, dict):
        raise ParseError("OpenAPI spec must be a JSON object")
    return data


def _resolve(data: dict[str, Any] | str | bytes) -> dict[str, Any]:
    """Resolve $refs using prance. Returns the normalized spec dict.

    Strict schema validation is skipped — a parser's job is to read what's
    there, not to police whether the spec is well-formed. Run a separate
    validator when you need that.
    """
    raw_dict = _coerce_spec(data)
    try:
        # ponytail: validate_spec=False — real-world specs often fail strict
        # validation; parser must still read them. Add a separate validator
        # tool if you want gatekeeping.
        parser = ResolvingParser(
            spec_string=json.dumps(raw_dict),
            strict=False,
            validate_spec=False,
        )
        spec = parser.specification
        return spec if isinstance(spec, dict) else dict(spec)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Failed to resolve OpenAPI spec: {e}") from e


def _has_http_methods(spec: dict[str, Any]) -> bool:
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return False
    for methods in paths.values():
        if isinstance(methods, dict) and any(m.lower() in _METHODS for m in methods):
            return True
    return False


def _param_type_and_constraints(param: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (simplified_type, constraints) for a Swagger 2.0 / OpenAPI 3.x param."""
    if "schema" in param and isinstance(param["schema"], dict):
        schema = param["schema"]
        type_ = schema.get("type", "string")
        constraints = {k: v for k, v in schema.items() if k in _CONSTRAINT_KEYS}
    else:
        type_ = param.get("type", "string")
        constraints = {k: v for k, v in param.items() if k in _CONSTRAINT_KEYS}
    return _TYPE_MAP.get(type_, "string"), constraints


def _convert_parameters(
    raw_params: list[dict[str, Any]],
) -> tuple[list[Parameter], Parameter | None]:
    """Convert raw params into (query/path/header/form params, request body)."""
    params: list[Parameter] = []
    body: Parameter | None = None
    for p in raw_params:
        loc = p.get("in", "")
        name = p.get("name", "")
        type_, constraints = _param_type_and_constraints(p)
        required = bool(p.get("required", False))
        if loc == "body":
            body = Parameter(
                name=name or "body",
                location="body",
                type=type_,
                required=required,
                description=p.get("description", ""),
                example=p.get("example"),
                constraints=constraints,
            )
        elif loc in _VALID_LOCATIONS:
            params.append(
                Parameter(
                    name=name,
                    location=loc,
                    type=type_,
                    required=required,
                    description=p.get("description", ""),
                    example=p.get("example") or p.get("x-example"),
                    constraints=constraints,
                )
            )
    return params, body


def _build_body_from_request_body(rb: dict[str, Any]) -> Parameter:
    """OpenAPI 3.x: pull a body Parameter out of requestBody.content."""
    content = rb.get("content") or {}
    json_media: dict[str, Any] = {}
    if isinstance(content, dict):
        if "application/json" in content and isinstance(content["application/json"], dict):
            json_media = content["application/json"]
        elif content:
            first = next(iter(content.values()))
            if isinstance(first, dict):
                json_media = first
    schema = json_media.get("schema") if isinstance(json_media, dict) else None
    type_ = (schema or {}).get("type", "object") if isinstance(schema, dict) else "object"
    return Parameter(
        name="body",
        location="body",
        type=_TYPE_MAP.get(type_, "object"),
        required=bool(rb.get("required", False)),
        description="",
        example=None,
        constraints={},
    )


def _convert_responses(raw_responses: Any) -> list[Response]:
    """Convert raw responses dict into Response objects."""
    if not isinstance(raw_responses, dict):
        return []
    return [
        Response(status_code=str(code), description=info.get("description", ""))
        for code, info in raw_responses.items()
        if isinstance(info, dict)
    ]


class OpenAPIParser:
    """Parser for Swagger 2.0 and OpenAPI 3.x specs."""

    name = "openapi"
    version = "1.0"

    def can_parse(self, data: dict[str, Any] | str | bytes) -> bool:
        try:
            spec = _coerce_spec(data)
        except ParseError:
            return False
        return ("openapi" in spec or "swagger" in spec) and _has_http_methods(spec)

    def parse(self, data: dict[str, Any] | str | bytes) -> list[Endpoint]:
        spec = _resolve(data)
        endpoints: list[Endpoint] = []
        paths = spec.get("paths")
        if not isinstance(paths, dict):
            return endpoints
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in _METHODS or not isinstance(operation, dict):
                    continue
                params, body = _convert_parameters(operation.get("parameters") or [])
                rb = operation.get("requestBody")
                if isinstance(rb, dict):
                    body = _build_body_from_request_body(rb)
                endpoints.append(
                    Endpoint(
                        path=path,
                        method=HttpMethod(method.upper()),
                        summary=operation.get("summary", ""),
                        description=operation.get("description", ""),
                        tags=list(operation.get("tags") or []),
                        operation_id=operation.get("operationId", ""),
                        parameters=params,
                        request_body=body,
                        responses=_convert_responses(operation.get("responses")),
                        raw=operation,
                    )
                )
        _log.debug("openapi parser produced %d endpoints", len(endpoints))
        return endpoints


# Self-register
ParserRegistry.register(OpenAPIParser())
