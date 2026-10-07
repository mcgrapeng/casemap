from __future__ import annotations

import pytest
from pydantic import ValidationError

from casemap.models.endpoint import Endpoint, HttpMethod, Parameter, Response


class TestHttpMethod:
    def test_string_values(self):
        assert HttpMethod.GET == "GET"
        assert HttpMethod.POST == "POST"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            HttpMethod("INVALID")


class TestParameter:
    def test_minimal(self):
        p = Parameter(name="id", location="query", type="string", required=True)
        assert p.name == "id"
        assert p.location == "query"
        assert p.required is True
        assert p.description == ""
        assert p.constraints == {}

    def test_full(self):
        p = Parameter(
            name="limit",
            location="query",
            type="integer",
            required=False,
            description="max results",
            example=10,
            constraints={"min": 1, "max": 100},
        )
        assert p.example == 10
        assert p.constraints["max"] == 100


class TestResponse:
    def test_construct(self):
        r = Response(status_code="200", description="success")
        assert r.status_code == "200"


class TestEndpoint:
    def test_minimal(self):
        ep = Endpoint(path="/users", method=HttpMethod.GET)
        assert ep.path == "/users"
        assert ep.method == HttpMethod.GET
        assert ep.tags == []
        assert ep.parameters == []
        assert ep.responses == []
        assert ep.request_body is None

    def test_with_params_and_responses(self):
        ep = Endpoint(
            path="/users/{id}",
            method=HttpMethod.POST,
            summary="Create user",
            tags=["users"],
            parameters=[Parameter(name="id", location="path", type="string", required=True)],
            responses=[Response(status_code="200"), Response(status_code="404")],
        )
        assert len(ep.parameters) == 1
        assert len(ep.responses) == 2

    def test_invalid_method_raises(self):
        with pytest.raises(ValidationError):
            Endpoint(path="/x", method="WRONG")  # type: ignore[arg-type]
