"""Postman v2.1 collection parser."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from casemap._internal.exceptions import ParseError
from casemap._internal.logger import get_logger
from casemap.models.endpoint import Endpoint, HttpMethod, Parameter, Response
from casemap.parsers.base import ParserRegistry

_log = get_logger("parsers.postman")
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _walk_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recursively flatten nested item groups."""
    flat: list[dict[str, Any]] = []
    for it in items:
        if "item" in it:
            flat.extend(_walk_items(it["item"]))
        elif "request" in it:
            flat.append(it)
    return flat


def _normalize_type(value: str) -> str:
    """Postman values are always strings; map to simplified type."""
    if value.isdigit():
        return "integer"
    if value.lower() in ("true", "false"):
        return "boolean"
    try:
        float(value)
        return "number"
    except ValueError:
        return "string"


def _endpoint_from_item(item: dict[str, Any]) -> Endpoint | None:
    req = item.get("request") or {}
    method = (req.get("method") or "").upper()
    if method not in _METHODS:
        return None
    url_raw = ""
    url_obj = req.get("url") or {}
    if isinstance(url_obj, dict):
        url_raw = url_obj.get("raw", "")
    elif isinstance(url_obj, str):
        url_raw = url_obj
    if not url_raw:
        return None
    parsed = urlparse(url_raw)
    path = parsed.path or "/"
    params: list[Parameter] = []
    qs = parse_qs(parsed.query)
    for name, values in qs.items():
        params.append(
            Parameter(
                name=name,
                location="query",
                type=_normalize_type(values[0]) if values else "string",
                required=False,
                example=values[0] if values else None,
            )
        )
    body = req.get("body")
    request_body: Parameter | None = None
    if isinstance(body, dict) and body.get("mode") == "raw":
        request_body = Parameter(
            name="body",
            location="body",
            type="object",
            required=False,
            example=body.get("raw", ""),
        )
    for h in req.get("header") or []:
        if not isinstance(h, dict):
            continue
        params.append(
            Parameter(
                name=h.get("key", ""),
                location="header",
                type="string",
                required=False,
                example=h.get("value"),
            )
        )
    description = req.get("description", "")
    if not isinstance(description, str):
        description = ""
    return Endpoint(
        path=path,
        method=HttpMethod(method),
        summary=item.get("name", ""),
        description=description,
        parameters=params,
        request_body=request_body,
        responses=[Response(status_code="200", description="(postman) inferred")],
        raw=req,
    )


class PostmanParser:
    name = "postman"
    version = "1.0"

    def can_parse(self, data: dict[str, Any] | str | bytes) -> bool:
        if isinstance(data, (str, bytes)):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False
        if not isinstance(data, dict):
            return False
        schema = (data.get("info") or {}).get("schema", "")
        return "postman.com" in schema and "item" in data

    def parse(self, data: dict[str, Any] | str | bytes) -> list[Endpoint]:
        if isinstance(data, (str, bytes)):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise ParseError("Postman input must be a JSON object")
        items = _walk_items(data.get("item") or [])
        out: list[Endpoint] = []
        for it in items:
            ep = _endpoint_from_item(it)
            if ep is not None:
                out.append(ep)
        _log.debug("postman parser produced %d endpoints", len(out))
        return out


ParserRegistry.register(PostmanParser())
